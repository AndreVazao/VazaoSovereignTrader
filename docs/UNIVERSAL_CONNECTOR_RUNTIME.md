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

## Exact-HEAD verification checkpoint — 2026-11-22 12:52 UTC

**Repository:** `AndreVazao/VazaoSovereignTrader`  
**Main SHA:** `05d4e7c9123e29780d26b12b56fba3f20d5440e7`  
**Active PR:** [#578](https://github.com/AndreVazao/VazaoSovereignTrader/pull/578), Draft, open, base `main`, mergeable/clean, not merged.  
**Current PR head:** read live metadata from [PR #578](https://github.com/AndreVazao/VazaoSovereignTrader/pull/578) before acting. **Last code-bearing SHA with all four applicable workflows green:** `121b10d187b80f42625cf23ac78881fb209a2d09`.

All four applicable code workflows completed successfully on that exact HEAD:

- [Python tests #45007660609](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45007660609) — **PASS**, 1,613 passed, 4 skipped, 96 subtests passed.
- [PAPER lifecycle/safety #45007660634](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45007660634) — **PASS**, 82 passed.
- [Connector sandbox Linux #45007660575](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45007660575) — **PASS**, 69 passed; builds the packaged CPython runtime and runs the real runtime/worker probes inside Bubblewrap.
- [Windows EXE/installer #45007660587](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45007660587) — **PASS**, both `build-exe` and `build-installer`. The installer job completed previous-version silent install, in-place upgrade, launch, PAPER health check, silent uninstall, process/task cleanup and Learning Vault SHA-256 preservation.

Windows artifacts from run #45007660587 (both unexpired when checked):
- [Portable Windows ZIP, artifact 14748651526](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45007660587/artifacts/14748651526), 65,932,024 bytes; upload-artifact archive SHA-256 `24c6cf95c5378290b24c6c4d00850b3ff4f2750b1ebbe56d04e16fec0e7023de`.
- [Windows installer ZIP, artifact 14748438404](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45007660587/artifacts/14748438404), 233,807,991 bytes; upload-artifact archive SHA-256 `731309b9a0efad900473c9c415ef8126e549b7cbea13135e9bbc413c2f4e891f`.

The successful Vercel preview comment is informational only and is not code-test evidence. No Android workflow was triggered by this PR's changed paths. No Snyk result was present in the exact-HEAD checks.

After those workflow runs, two documentation-only commits were added: [d9fe13d](https://github.com/AndreVazao/VazaoSovereignTrader/commit/d9fe13d8a20e2024dc2180c08e47f995ca3082bb) and [d2e5391](https://github.com/AndreVazao/VazaoSovereignTrader/commit/d2e5391d59af3ff823726978bacdfad86ba2fd94). They update only `docs/UNIVERSAL_CONNECTOR_RUNTIME.md` and `docs/PROJECT_CONTEXT.md`. The current branch HEAD is therefore `d2e5391d59af3ff823726978bacdfad86ba2fd94`; the green code-workflow evidence remains attached to code-bearing SHA `121b10d187b80f42625cf23ac78881fb209a2d09`. These documentation paths are outside the Python/PAPER/Windows/Linux code-workflow path filters, so those workflows were not re-triggered on the documentation-only HEAD. Do not describe `d2e5391d59af3ff823726978bacdfad86ba2fd94` as having a fresh code test run.

**What the Linux CI now proves:** the packaged CPython runtime is built from the selected trusted interpreter, imported and exercised inside Bubblewrap; the existing `IsolatedConnectorAdapter` multiprocessing spawn path, bounded IPC, timeout and process-group cleanup are exercised from inside that namespace. This is materially beyond the earlier static-probe-only stage.

**What it does not prove:** production launch is still not integrated. The trusted production parent/supervisor does not yet construct the strict manifest-backed Bubblewrap command and launch the worker through it before adapter code executes. The CI probe enters Bubblewrap first, then starts the adapter inside it. This is not yet the production lifecycle.

**Do not merge or enable third-party connectors yet.** Remaining security gates:
1. Authenticate/sign the runtime inventory and bind it to the installer/package trust chain; hashes alone do not establish authenticity.
2. Establish and verify root-owned, immutable package paths in the actual installer/runtime, including replacement/TOCTOU protection between validation and mount.
3. Implement the trusted parent/supervisor launch path using only the manifest-backed builder; no fallback to broad host mounts or unsandboxed multiprocessing when strict mode is required.
4. Integrate only after the launcher/lifecycle tests pass; keep `ConnectorRegistry` disconnected from untrusted connector execution meanwhile.
5. Keep Linux egress deny-all until a separately reviewed provider-specific HTTPS policy and DNS/redirect/private-address/proxy escape tests exist.
6. Implement independent Windows filesystem and network isolation; Job Objects remain process/resource controls only.
7. Perform physical target-PC validation; CI is not evidence of the user's PC.

The repository inventory at this checkpoint returned 33 branches including `main`, exactly one open PR (#578), and no formal GitHub Releases. Branch listing reported `protected=false` for `main`; the rulesets endpoint returned an empty list, while the branch-protection endpoint returned 403 to this integration. Therefore required branch protection cannot be confirmed and should be checked in repository settings by an authorized maintainer.

VST remains PAPER-only. No credentials, exchange accounts, LIVE permissions, orders, transfers or financial operations are used or authorized.
