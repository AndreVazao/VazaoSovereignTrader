# Connector Worker Sandbox — implementation plan

**Status (2026-11-20):** The explicit runtime-manifest validator is implemented. PR #578 now has an opt-in manifest-backed Bubblewrap command-construction path that revalidates the manifest and emits only explicit read-only mounts; the legacy compatibility path still uses broad host roots. Real Bubblewrap execution of the manifest-backed path, worker lifecycle integration, provider egress policy and Windows filesystem/network isolation remain blocked.
**Date:** 2026-11-20
**Base:** `05d4e7c9123e29780d26b12b56fba3f20d5440e7` (PR #577 merge commit; includes PR #576)

## Current enforced worker controls on main

The one-shot worker currently provides:
- POSIX `RLIMIT_AS` and `RLIMIT_CPU`, preserving stricter inherited soft and hard limits.
- Windows Job Object per-process memory and CPU-time limits with kill-on-close.
- Dedicated POSIX process group / Windows Job Object process-tree cleanup.
- Credential-shaped environment variable removal before adapter factory execution.
- Bounded JSON IPC and sanitized errors.

These controls do not isolate filesystem access or restrict network egress. The worker remains disconnected from the live connector registry. Do not execute untrusted third-party adapters.

## Work in the current PR

`PC_ENGINE/core/connector_runtime_manifest.py` now validates an explicit runtime closure:
- Requires an absolute, existing, non-symlinked executable and explicit regular-file/directory entries.
- Rejects broad or sensitive directory roots, duplicates, type conflicts, symlinks, missing paths and overlapping mounts.
- Rejects hard-linked runtime files and group/world-writable runtime files or directories, reducing alias-based mutation and untrusted-owner replacement risks.
- Recursively rejects symlinks, special files, hard-linked files and group/world-writable nested files/directories inside every exposed runtime directory; TOCTOU protection still requires immutable packaged roots and revalidation immediately before mounting.
- Rejects files or the executable hidden beneath a separately declared directory mount; the directory mount itself is the sole exposure declaration for its contents.
- Does not run `ldd`, execute discovery tools, infer dependencies or widen mounts.
- Produces immutable mount records and exposes `revalidate_runtime_manifest()` to reconstruct and re-inspect every declared source immediately before command construction.

`PC_ENGINE/core/connector_worker_sandbox.py` now supports two deliberately separate paths:
- Uses separate user, PID, IPC, UTS and network namespaces; host network access is denied.
- Clears the inherited environment and sets only a minimal PATH, HOME and TMPDIR.
- Legacy compatibility path: mounts selected broad system/runtime roots read-only, masks `/usr/local`, and sets PATH to `/usr/bin`. This path is not a minimal runtime and remains unsuitable for untrusted third-party connectors.
- Manifest-backed path: rejects simultaneous legacy `runtime_roots`, revalidates the manifest, requires `command[0]` to match the declared executable, creates only empty destination parents, mounts only explicit manifest entries read-only, sets PATH to `/work/bin`, and does not mount `/usr`, `/lib`, `/bin`, `/etc/ld.so.cache` or the host certificate tree. Private `/tmp` and `/work` tmpfs mounts are created before explicit mounts so declared destinations beneath those parents are not shadowed.
- Does not mount the host root, home, VST data, Learning Vault, credentials or host temporary directory.
- Uses private `/tmp` and `/work` tmpfs mounts with explicit size limits (16 MiB and 64 MiB by default; each is capped at 256 MiB).
- Canonicalizes the executable path and rejects broad/sensitive runtime roots, undeclared executable paths, invalid tmpfs sizes and missing/non-executable Bubblewrap.
- Fails closed on unsupported platforms or setup errors.

A dedicated Linux GitHub Actions workflow installs Bubblewrap and GCC and runs real sandbox execution tests. The legacy-path test attempts to read a host-only file, connect to a host loopback listener, verify inherited environment variables are cleared, verify normalized HOME/TMPDIR values, and inspect both private `/tmp` and `/work` tmpfs capacities. A manifest-backed static probe checks that `/usr/bin/id`, `/etc/passwd` and an undeclared host marker are inaccessible while the explicitly mounted static executable runs. Both integration tests must execute, not silently skip, in that workflow.

**Additional manifest hardening (2026-11-20):** regular runtime files must have a single hard link and must not be group/world writable; runtime directories must not be group/world writable. Focused tests cover each rejection. This narrows alias and permission risks but does not eliminate privileged-owner replacement or TOCTOU races; the packager must still provide immutable runtime roots and production launch must revalidate immediately before mounting.

**Security blocker — broad runtime exposure (2026-11-20):** the builder still mounts broad read-only `/usr`, `/lib`, `/bin` and related roots, so host tools and binaries can remain visible/callable. Masking `/usr/local` does not make this a minimal runtime. The manifest validator is groundwork only: until `build_linux_bwrap_command` consumes a validated manifest and mounts only its explicit entries, this blocker remains open. The next implementation step is to make manifest-backed mounting the only accepted execution path, create only the required empty destination parents, reject any undeclared executable or dependency, and add real Bubblewrap tests proving host executables and unrelated host files are absent. Do not enable connector execution in the meantime.\n\n**Important limitations:** this remains a command builder plus an isolated execution test. It is not yet called by `IsolatedConnectorAdapter`, does not provision or clean a production worker lifecycle, and does not provide provider-specific HTTPS egress. Windows filesystem/network sandboxing is not implemented. Do not describe this branch as a complete sandbox.

## Required security contract

The worker may be enabled for an adapter only when every required control is positively verified. Missing platform support, policy ambiguity, setup failure, or enforcement-test failure must deny execution.

### Filesystem
- Use a fresh per-invocation writable area with an enforced size limit.
- Do not expose the VST data directory, configuration, Learning Vault, user home, SSH material, browser profiles or application secrets.
- Mount only explicitly declared, reviewed runtime roots read-only.
- Enforce the boundary in the operating system, not only through Python path checks or changing the current directory.
- Keep writable scratch ephemeral and bounded; return only bounded, sanitized output through worker IPC.
- Test traversal, symlink/reparse-point escapes, hard links, inherited handles, temporary-directory discovery and child-process access.
- Treat path validation followed by a later mount as a potential time-of-check/time-of-use boundary; production integration must keep runtime roots immutable for the launch or use an fd-based launch design.

### Network egress
- Deny by default. The current Bubblewrap prototype denies all network; provider-specific allowlisting is not implemented.
- Future providers may reach only explicitly approved HTTPS destinations and required DNS resolution.
- Resolve and validate every destination; reject loopback, link-local, private, multicast, unspecified, reserved and cloud metadata addresses unless a narrowly documented exception is approved.
- Prevent DNS rebinding and redirect-based policy escape; validate the connected peer address, not only the original hostname.
- Block arbitrary ports, raw sockets, local-network scanning, proxy inheritance and access to local VST services.
- Apply policy below the Python adapter layer (OS firewall/network namespace/AppContainer or equivalent). URL validation and monkey-patching sockets are not enforcement.
- Treat redirects, alternate IP literals, IPv4-mapped IPv6, IDNA names, CNAME chains, proxy variables and connection reuse as explicit test cases.

### Platform enforcement
- Linux: the legacy Bubblewrap path has real CI coverage for host-file denial, host-loopback denial, inherited-environment removal, normalized HOME/TMPDIR and bounded tmpfs. The new opt-in manifest-backed builder has command-construction and source-revalidation tests plus a static executable probe intended to verify that undeclared `/usr/bin/id`, `/etc/passwd` and a host marker are inaccessible. Its first exact-HEAD CI run is pending. Still required: packaged Python closure execution, worker lifecycle integration, adversarial path/child-process tests, bounded cleanup, restricted syscalls/capabilities and reviewed provider egress policy. The broad `/usr` mount remains a blocker in the legacy path; the manifest-backed path must be the only path permitted for untrusted workers.
- Windows: implement AppContainer/restricted token plus Job Object, explicit capability policy, private scratch ACLs and Windows Firewall/WFP enforcement. Job Objects alone do not provide filesystem or network isolation.
- Do not claim platform parity until both platforms have independent negative tests proving that denied file and network access actually fails.

## Integration gates

1. Require the dedicated Linux Bubblewrap workflow to pass on the exact PR HEAD.
2. Extend Linux negative tests for path traversal, symlink escapes, child processes, cleanup, crash, timeout and policy reload.
3. Implement the equivalent Windows OS boundary or keep Windows adapter execution disabled.
4. Verify the worker cannot read VST configuration, Vault files, user secrets or local service endpoints.
5. Define provider-specific egress allowlists and prove redirects, DNS rebinding and private-address escapes are blocked before enabling any network access.
6. Integrate the sandbox into the worker supervisor only after all applicable platform gates pass.
7. Keep the worker disconnected from `ConnectorRegistry` until the integration gates pass.
8. Enable only first-party, public, read-only providers initially; no credentials, private account scopes, trading, transfers or withdrawals.

## Explicit non-goals

- No account linking or credential forwarding.
- No private exchange APIs.
- No LIVE mode or financial execution.
- No cloud sandbox provisioning or paid service activation.
- No claim of physical Windows/Linux validation from CI alone.

## Acceptance evidence

The eventual integration PR must include:
- A platform-by-platform enforcement matrix with exact OS APIs/features.
- Negative tests demonstrating denied file reads, denied network access and bounded writable storage.
- Exact-head Python, PAPER, Linux and Windows workflow results.
- Sanitized diagnostics proving setup failures fail closed.
- Documentation distinguishing implemented controls from deferred controls.

Until all gates pass, the worker is resource-limited and the Linux sandbox command builder is a prototype; neither is a complete production security sandbox.
