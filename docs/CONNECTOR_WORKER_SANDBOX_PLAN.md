# Connector Worker Sandbox — implementation plan

**Status:** Linux policy-command prototype added; no worker integration and no complete sandbox yet.
**Date:** 2026-11-17
**Base:** `f4b5811b59f71efcc4d2fcbcf3441efd05cb595e` (PR #576 squash merge)

## Current enforced controls

The one-shot worker currently provides:
- POSIX `RLIMIT_AS` and `RLIMIT_CPU`, preserving stricter inherited limits.
- Windows Job Object per-process memory and CPU-time limits with kill-on-close.
- Dedicated POSIX process group / Windows Job Object process-tree cleanup.
- Credential-shaped environment variable removal before adapter factory execution.
- Bounded JSON IPC and sanitized errors.

These controls do not isolate filesystem access or restrict network egress. The worker remains disconnected from the live connector registry. Do not execute untrusted third-party adapters.

## Work added in this branch

`PC_ENGINE/core/connector_worker_sandbox.py` adds a Linux Bubblewrap argv builder:
- Uses separate user, PID, IPC, UTS and network namespaces; network is denied entirely.
- Clears the inherited environment.
- Mounts selected system runtime roots read-only, plus explicitly declared runtime roots.
- Exposes only a private scratch directory as writable `/work`; does not bind the host root, home, VST data or credentials.
- Rejects missing Bubblewrap, non-Linux use, non-private scratch permissions, undeclared executable paths and a root filesystem runtime mount.

Focused tests cover the generated deny-network policy, forbidden host-root bind, undeclared executable, scratch permissions and fail-closed behavior when Bubblewrap is absent.

**Important limitations:** this is command construction only. It does not launch a worker, prove that the host kernel permits namespaces, impose a scratch disk quota, or provide provider-specific HTTPS egress. It is not connected to `IsolatedConnectorAdapter`. The generated command must still be validated by real Bubblewrap execution and adversarial tests on Linux CI. Windows filesystem/network sandboxing is not implemented. Do not describe this branch as a complete sandbox.

## Required security contract

The worker may be enabled for an adapter only when every required control is positively verified. Missing platform support, policy ambiguity, setup failure, or enforcement-test failure must deny execution.

### Filesystem

- Give each invocation a fresh private working directory with restrictive permissions and an enforced size limit.
- Do not expose the VST data directory, configuration, Learning Vault, user home, SSH material, browser profiles, or application secrets.
- Mount or expose only explicitly declared read-only provider/runtime resources and a bounded writable scratch directory.
- Enforce the boundary in the operating system, not only through Python path checks or changing the current directory.
- Remove scratch data after worker termination; preserve only explicitly approved, size-bounded diagnostic output with secrets redacted.
- Test traversal, symlink/reparse-point escapes, hard links, inherited handles, temporary-directory discovery, and child-process access.

### Network egress

- Deny by default. Permit only provider-specific HTTPS destinations and required DNS resolution.
- Resolve and validate every destination; reject loopback, link-local, private, multicast, unspecified, reserved, and cloud metadata addresses unless a narrowly documented exception is approved.
- Prevent DNS rebinding and redirect-based policy escape; validate the connected peer address, not only the original hostname.
- Block arbitrary ports, raw sockets, local-network scanning, proxy inheritance, and access to local VST services.
- Apply policy below the Python adapter layer (OS firewall/network namespace/AppContainer or equivalent). URL validation and monkey-patching sockets are not enforcement.
- Treat redirects, alternate IP literals, IPv4-mapped IPv6, IDNA names, CNAME chains, proxy variables, and connection reuse as explicit test cases.

### Platform enforcement

- Linux: validate Bubblewrap user/mount/network namespaces on CI; add a bounded scratch filesystem, restricted syscalls/capabilities and explicit policy. Current prototype denies all network; provider-specific allowlisting remains future work.
- Windows: implement AppContainer/restricted token plus Job Object, explicit capability policy, private scratch ACLs, and Windows Firewall/WFP enforcement. Job Objects alone do not provide filesystem or network isolation.
- Do not claim parity until both platforms have independent negative tests proving that denied file and network access actually fails.

## Integration gates

1. Execute the Linux sandbox command in a real integration test; prove host-file reads, host sockets and network access are denied.
2. Add bounded scratch storage and adversarial tests for filesystem escape, network escape, child processes, cleanup, crash, timeout and policy reload.
3. Implement the equivalent Windows OS boundary or keep Windows adapter execution disabled.
4. Run the worker test suite on Linux and Windows CI.
5. Verify the worker cannot read VST configuration, Vault files, user secrets, or local service endpoints.
6. Verify each provider can reach only its declared public endpoints and cannot redirect outside the allowlist.
7. Keep the worker disconnected from `ConnectorRegistry` until all applicable gates pass.
8. Enable only first-party, public, read-only providers initially; no credentials, private account scopes, trading, transfers, or withdrawals.

## Explicit non-goals

- No account linking or credential forwarding.
- No private exchange APIs.
- No LIVE mode or financial execution.
- No cloud sandbox provisioning or paid service activation.
- No claim of physical Windows/Linux validation from CI alone.

## Acceptance evidence

The eventual pull request must include:
- A platform-by-platform enforcement matrix with exact OS APIs/features.
- Negative tests demonstrating denied file reads and denied network connections.
- Exact-head Python, PAPER, Linux and Windows workflow results.
- Sanitized diagnostics proving setup failures fail closed.
- Documentation that distinguishes implemented controls from deferred controls.

Until all gates pass, the worker is resource-limited and the Linux sandbox command builder is only a prototype; neither is a complete security sandbox.
