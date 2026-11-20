# Universal Connector Runtime — VST

**Status date:** 2026-11-20  
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

PR #578 adds `PC_ENGINE/core/connector_runtime_manifest.py`, which validates explicit executable/file/directory entries and rejects broad/sensitive directory roots, symlinks, special files, hard links, group/world-writable entries, duplicate/type-conflicting paths and overlapping mounts. Directory trees are inspected recursively. The validator does not discover dependencies, execute `ldd`, mount files or integrate with worker launch.

**Critical security blocker:** `build_linux_bwrap_command` still mounts broad read-only host roots including `/usr`, `/lib` and `/bin`, and does not consume the manifest. Read-only does not mean isolated: host executables and unrelated files can remain visible/callable. Masking `/usr/local` is not sufficient. The manifest is not integrated with the worker supervisor, `IsolatedConnectorAdapter`, `ConnectorRegistry` or installer. Do not load untrusted third-party adapters.

## Required Linux acceptance gates

1. Bubblewrap must consume a launch-time revalidated explicit manifest and mount only declared runtime files/directories; remove all broad host runtime mounts from the manifest-backed path.
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

## Exact-HEAD verification checkpoint — 2026-11-20

For PR #578 HEAD `22379427f8c81a5103d2e3379bd083196a4b9d50`, GitHub Actions reported success for Python tests, PAPER smoke, Connector sandbox Linux, Windows EXE and Windows installer. The installer job completed previous-version install, upgrade, launch, health, uninstall and Learning Vault preservation smoke. This is CI evidence only; physical PC validation remains pending. Vercel previews are informational, not code tests. Android and unrelated workflows were not triggered by this PR's path filters.
