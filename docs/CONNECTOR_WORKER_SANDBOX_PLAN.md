# Connector Worker Sandbox — implementation plan

**Status:** Linux Bubblewrap command builder now creates bounded private tmpfs mounts and has a real enforcement test; worker integration and cross-platform sandboxing are still incomplete.
**Date:** 2026-11-17
**Base:** `f4b5811b59f71efcc4d2fcbcf3441efd05cb595e` (PR #576 squash merge)

## Current enforced worker controls on main

The one-shot worker currently provides:
- POSIX `RLIMIT_AS` and `RLIMIT_CPU`, preserving stricter inherited soft and hard limits.
- Windows Job Object per-process memory and CPU-time limits with kill-on-close.
- Dedicated POSIX process group / Windows Job Object process-tree cleanup.
- Credential-shaped environment variable removal before adapter factory execution.
- Bounded JSON IPC and sanitized errors.

These controls do not isolate filesystem access or restrict network egress. The worker remains disconnected from the live connector registry. Do not execute untrusted third-party adapters.

## Work in the current PR

`PC_ENGINE/core/connector_worker_sandbox.py` builds a Linux Bubblewrap invocation:
- Uses separate user, PID, IPC, UTS and network namespaces; host network access is denied.
- Clears the inherited environment and sets only a minimal PATH, HOME and TMPDIR.
- Mounts selected system/runtime roots read-only; masks existing `/usr/local/etc`, `/usr/local/var`, and `/usr/local/bin` paths with private tmpfs mounts; fails closed if a mask target is a symlink or non-directory. The sandbox PATH is limited to `/usr/bin`.
- Does not mount the host root, home, VST data, Learning Vault, credentials or host temporary directory.
- Uses private `/tmp` and `/work` tmpfs mounts with explicit size limits (16 MiB and 64 MiB by default; each is capped at 256 MiB).
- Canonicalizes the executable path and rejects broad/sensitive runtime roots, undeclared executable paths, invalid tmpfs sizes and missing/non-executable Bubblewrap.
- Fails closed on unsupported platforms or setup errors.

A dedicated Linux GitHub Actions workflow installs Bubblewrap and runs a real sandbox execution test. The test attempts to read a host-only file, connect to a host loopback listener, verify inherited environment variables are cleared, verify normalized HOME/TMPDIR values, and inspect both private `/tmp` and `/work` tmpfs capacities. The test must execute, not silently skip, in that workflow.

**Additional mount audit (2026-11-18):** masking the complete `/usr/local` subtree and keeping PATH limited to `/usr/bin` reduces local configuration/state/executable exposure. However, the broad read-only `/usr` mount still exposes other host-provided executables/tools, which may be callable. Read-only access is still host content exposure, not a complete isolation boundary. Before production, replace the broad runtime mount with an explicit minimal runtime closure (interpreter, required shared libraries, CA roots, and narrowly approved support files), omit host `/usr/local` entirely unless a reviewed dependency requires it, and use a minimal PATH. Add negative tests for host executable discovery/callability and mount/symlink escape cases. This is a security blocker, not an accepted residual risk.\n\n**Important limitations:** this remains a command builder plus an isolated execution test. It is not yet called by `IsolatedConnectorAdapter`, does not provision or clean a production worker lifecycle, and does not provide provider-specific HTTPS egress. Windows filesystem/network sandboxing is not implemented. Do not describe this branch as a complete sandbox.

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
- Linux: real Bubblewrap execution is tested in CI for host-file denial, host-loopback denial, inherited-environment removal, normalized HOME/TMPDIR and both bounded tmpfs mounts. Still required: adversarial path/child-process tests, bounded lifecycle cleanup, restricted syscalls/capabilities and a reviewed provider egress policy. The broad `/usr` runtime mount is not treated as safe by itself; existing local configuration/state directories below it are now masked.
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
