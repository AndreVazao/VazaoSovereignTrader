# Universal Connector Runtime — VST

**Status date:** 2026-11-21  
**Scope:** first-party public market-data adapters and the security boundaries required before any third-party connector execution. This document describes verified implementation, not planned capability.

## Implemented on main

- A typed provider manifest and capability contract lives in `PC_ENGINE/core/platform_connectors.py`.
- `ConnectorRegistry` enforces explicit owner grants and provider verification, read-only capability allowlists, per-provider rolling request limits, JSON request/response size limits, detached request data and sanitized adapter errors.
- The built-in `CcxtPublicMarketDataAdapter` supports bounded public `ticker`, `ohlcv` and `order_book` reads without API keys or private/account methods.
- The engine registers only venues explicitly present in `radar.polling_exchanges`, while the engine is in PAPER mode and Radar is observational-only.
- Registered adapters reuse existing unauthenticated `MarketRadar` CCXT clients and per-client locks.
- On-demand public connector reads are capped at 12 requests/minute per provider, in addition to CCXT rate limiting.
- The connector API is owner-authenticated with `read_private_state`; responses are `no-store`, and credential-shaped request fields are rejected before adapter execution.

## Worker resource boundary on main

PR #576 is included in main through PR #577 merge commit `05d4e7c9123e29780d26b12b56fba3f20d5440e7`:
- POSIX workers apply `RLIMIT_AS` and `RLIMIT_CPU`, preserving stricter inherited limits.
- Windows workers use a kill-on-close Job Object with process/memory/CPU controls.
- POSIX process groups and Windows Job Objects terminate worker descendants on timeout.
- Credential-shaped inherited environment variables are removed before adapter factory execution.
- JSON IPC is bounded and worker errors are sanitized.

These controls bound resource use and process lifetime; they do not isolate filesystem access or restrict network egress.

## Linux Bubblewrap prototype and active PR #578

PR #577 is merged. The active security groundwork is PR #578, branch `feat/minimal-python-runtime-closure-2026-11-20`, currently Draft and not merged.

The merged Bubblewrap prototype provides:
- user, PID, IPC, UTS and network namespaces; network is denied;
- a cleared environment and bounded private `/tmp` and `/work` tmpfs mounts;
- a real Linux CI enforcement test for host-file denial, loopback denial, inherited-environment removal and tmpfs limits.

PR #578 adds `PC_ENGINE/core/connector_runtime_manifest.py`, which validates explicit executable/file/directory entries and rejects source paths overlapping host-owned sensitive/system roots (including nested descendants and ancestor mounts), symlinks, special files, hard links, group/world-writable entries, duplicate/type-conflicting paths and overlapping mounts. Directory trees are inspected recursively. `revalidate_runtime_manifest()` reconstructs and rechecks the exact manifest immediately before command construction. It does not discover dependencies or execute `ldd`.

**Current builder split:** `build_linux_bwrap_command(..., runtime_manifest=...)` now has a separate opt-in manifest-backed path. It rejects simultaneous legacy `runtime_roots`, revalidates the manifest, requires the command executable to match the manifest, creates only empty destination parents, sets a non-host PATH, creates private `/tmp` and `/work` first, and mounts only explicit entries read-only. It does not add `/usr`, `/lib`, `/bin`, `/etc/ld.so.cache` or the host CA tree. The legacy compatibility path still uses broad read-only host roots and remains unsuitable for untrusted connectors. A real Bubblewrap static-probe test is now included to check denial of `/usr/bin/id`, `/etc/passwd` and an undeclared host marker.

**Critical integration blocker:** the manifest-backed builder path is not called by `IsolatedConnectorAdapter`, the worker supervisor, `ConnectorRegistry` or installer. The real static probe is not yet validated by a new CI run on the latest HEAD, and the packaged Python interpreter/shared-library closure has not been tested. Do not load untrusted third-party adapters.

## Required Linux acceptance gates

1. Keep production worker launch fail-closed until the supervisor calls the manifest-backed builder; then ensure the manifest-backed path mounts only declared runtime files/directories and never falls back to broad host roots.
2. Create only empty destination parent directories needed for explicit mounts; reject overlapping, symlinked, mutable or changed paths. Packaged runtime roots must be immutable and protected against TOCTOU replacement between validation and launch.
3. Real Bubblewrap tests must prove the declared interpreter starts/imports while undeclared host executables, tools, unrelated files, host home, VST data, Learning Vault and credentials remain inaccessible.
4. Add adversarial path/traversal, symlink/hard-link, replacement race, child-process, crash and bounded cleanup tests.
5. Keep network deny-all until a separately reviewed provider-specific egress policy exists. Do not infer HTTPS access from a network namespace alone.

## Windows and lifecycle gates

Windows Job Objects provide process/resource control only. Filesystem and network isolation are not implemented. Before enabling third-party connectors, add a restricted-token/AppContainer or equivalent filesystem boundary, explicit network policy, private scratch ACLs and independent negative tests. Do not claim Linux/Windows sandbox parity until both platforms prove denied file and network access.

## Safety boundary

The current registry permits only `READ_ONLY_CAPABILITIES`. It rejects order creation/cancellation, transfers, withdrawals, profile mutation and interactive device control. Public CCXT reads do not use private exchange accounts. VST remains PAPER-only. No credentials, private accounts, LIVE trading or financial actions are authorized by this connector runtime.

## Other limits

- The registry currently executes adapters in-process; the resource-limited worker is not integrated into the registry execution path.
- Python cannot forcibly interrupt arbitrary synchronous third-party code running in-process.
- OAuth, private account reads, balances, statements, Android UI automation, browser automation and desktop automation are not live integrations in this increment.
- U-Hodler is not connected; no Android virtualization provider is provisioned.
- Human handoff remains mandatory for MFA, OTP, CAPTCHA, biometrics, consent and financial/security prompts.

## Exact-HEAD verification checkpoint — 2026-11-22

At PR #578 HEAD `e5c0e9fefbc6a69b3c91a9fce0e519aefd31fdc0`, all four applicable GitHub Actions workflows completed successfully on the exact same SHA:

- Python tests: run `44904591206`, job `test`.
- PAPER lifecycle/safety: run `44904591234`, job `PAPER lifecycle and safety boundaries`.
- Connector sandbox Linux: run `44904591241`, job `linux-bubblewrap-enforcement`.
- Windows EXE/installer: run `44904591213`; both `build-exe` and `build-installer` succeeded. The installer job ran previous-version install, upgrade, launch, health check, uninstall and Learning Vault preservation, then uploaded the artifact.

The installer lifecycle is no longer pending for this SHA. CI does not replace physical validation on the target PC. Vercel previews are not code-test evidence.

The Linux workflow still validates the manifest-backed static executable probe, not a packaged CPython runtime. The manifest-backed launcher is not integrated into `IsolatedConnectorAdapter` or a parent supervisor. Runtime authenticity/immutability, TOCTOU mitigation, bounded IPC under Bubblewrap, provider-specific egress and Windows filesystem/network isolation remain open. PR #578 remains Draft and must not be merged based only on green CI. Do not enable third-party connectors.
