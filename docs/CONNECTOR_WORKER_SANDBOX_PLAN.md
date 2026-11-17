# Connector Worker Sandbox — implementation plan

**Status:** design checkpoint; not an implemented security boundary.
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

## Required security contract

The worker may be enabled for an adapter only when every required control is positively verified. Missing platform support, policy ambiguity, setup failure, or enforcement-test failure must deny execution.

### Filesystem

- Give each invocation a fresh private working directory with restrictive permissions.
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

- Linux: evaluate an isolated user/network/mount namespace or a dedicated sandbox runtime with no host mounts by default, restricted syscalls/capabilities, cgroup limits, and explicit egress rules. Fail closed if required kernel features are unavailable.
- Windows: evaluate AppContainer/restricted token plus Job Object, explicit capability policy, private scratch ACLs, and Windows Firewall/WFP enforcement. Job Objects alone do not provide filesystem or network isolation.
- Do not claim parity until both platforms have independent negative tests proving that denied file and network access actually fails.

## Integration gates

1. Implement the OS boundary independently of provider adapters.
2. Add adversarial tests for filesystem escape, network escape, child processes, cleanup, crash, timeout, and policy reload.
3. Run the worker test suite on Linux and Windows CI.
4. Verify the worker cannot read VST configuration, Vault files, user secrets, or local service endpoints.
5. Verify each provider can reach only its declared public endpoints and cannot redirect outside the allowlist.
6. Keep the worker disconnected from `ConnectorRegistry` until all applicable gates pass.
7. Enable only first-party, public, read-only providers initially; no credentials, private account scopes, trading, transfers, or withdrawals.

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
- Exact-head Python, PAPER, Linux, and Windows workflow results.
- Sanitized diagnostics proving setup failures fail closed.
- Documentation that distinguishes implemented controls from deferred controls.

Until then, the worker is resource-limited but not a complete security sandbox.
