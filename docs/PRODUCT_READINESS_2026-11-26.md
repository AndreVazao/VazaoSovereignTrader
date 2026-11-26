# VST global product readiness — 2026-11-26

**Repository:** AndreVazao/VazaoSovereignTrader only  
**Audited main SHA:** `10e26cde4eca1d83ac22c34b5d4e32e2f55a4e15`  
**Audit boundary:** GitHub source, commit metadata, PR history, Actions check-runs/logs, artifacts, workflow path filters and current product documentation. No credentials, private exchange accounts, financial actions or other repositories were accessed.

## Executive assessment

The VST made material progress since the 2026-11-25 audit. PRs #598–#601 were integrated, completing deferred CCXT metadata discovery, collector progress diagnostics, cooperative cancellation around metadata loading, and cooperative-only shutdown for the supervised public market-data workers. The Windows uninstaller now aborts if the market-data supervisor cannot confirm `STOPPED`.

The exact current main SHA passes the full Python suite and the Windows EXE/installer workflows. The Windows installer workflow now also verifies that uninstall fails closed when the market-data health state is `DEGRADED`, then verifies a successful uninstall after the simulated fault is cleared.

**VST is not globally complete and is not yet accepted on the physical target PC.** CI evidence is stronger, but it does not establish real low-memory endurance, installed collector-supervisor lifecycle, production third-party connector isolation, full Learning Vault recovery/isolation, OOS research validity or Android/Linux release readiness.

Keep VST PAPER-only. Public market-data workers remain fixed, credential-free and read-only. Do not enable third-party connector execution.

## Repository inventory

- Default branch: `main`.
- Exact main SHA: `10e26cde4eca1d83ac22c34b5d4e32e2f55a4e15`.
- Open pull requests: **0** at audit time.
- Branch refs: **53 including main**. Retained branches are not active delivery lines merely because they exist.
- The retained branch `feat/connector-supervisor-launch-contract-2026-11-22` is diverged from current main (10 commits ahead / 23 behind). Do not reuse it without a fresh code review and rebase plan.
- Formal GitHub Releases: **none**.
- Current tag inventory: `mobile-v0.4.1` at `8a5a54b45b3a8358c136efc0615b088a305f4ef7`, not current main.
- Main reports `protected=false`; the repository rulesets endpoint returned an empty list. The branch-protection endpoint returned 403 to this integration. No settings were changed; the repository owner must verify and enforce required reviews/status checks in GitHub settings.

### Recent integrations

| PR | Change | Merge time (UTC) | Merge commit |
|---|---|---:|---|
| [#598](https://github.com/AndreVazao/VazaoSovereignTrader/pull/598) | Defer public exchange metadata loading | 2026-11-25 20:31:55 | `06b427d8274026d7071af28c700d0af15a7d7670` |
| [#599](https://github.com/AndreVazao/VazaoSovereignTrader/pull/599) | Expose PAPER collector progress/shutdown diagnostics | 2026-11-26 09:11:08 | `e1f435616a39207b1cf6521e26ceec08ecb8bd53` |
| [#600](https://github.com/AndreVazao/VazaoSovereignTrader/pull/600) | Bound CCXT metadata discovery cancellation | 2026-11-26 09:40:01 | `605d709da13e84acc97464f5d2c6e2307903f2ff` |
| [#601](https://github.com/AndreVazao/VazaoSovereignTrader/pull/601) | Cooperative-only public market-data worker shutdown; fail-closed uninstall | 2026-11-26 12:26:59 | `10e26cde4eca1d83ac22c34b5d4e32e2f55a4e15` |

Earlier #596 and #597 are also merged. PRs #536 and #541 remain historical only.

## Exact-main CI and artifacts

### Main SHA `10e26cde4eca1d83ac22c34b5d4e32e2f55a4e15`

- [Python tests — run 45819746452](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45819746452): **PASS**, 1,720 passed, 4 skipped, 101 subtests passed.
- [Windows EXE + installer — run 45819746055](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45819746055): **PASS**, both jobs.
  - EXE job: PowerShell helper syntax, Windows PowerShell 5.1 local-token helper generation/preservation/weak-token rejection (value not logged), DPAPI CurrentUser vault tests, constrained-memory PAPER policy tests, connector worker resource-boundary tests, adaptive resource sampling, EXE build and HTTP `/health` smoke.
  - Installer job: previous-version silent install, in-place upgrade, installed engine/worker-file checks, local engine health smoke, fail-closed uninstall when market-data health is simulated as `DEGRADED`, preservation of engine/worker files after the rejected uninstall, successful uninstall after clearing the simulated fault, and Learning Vault marker SHA-256 preservation.
- Current-main combined commit status surfaced only Vercel success. Vercel is not code-test evidence. No Snyk check was present on this exact main SHA. Snyk passed on PR #601's exact head `d92b65ce90784f07a6a7f3bf31d3fc614d0e8a22`, not the merge SHA.

Current-main Windows artifacts:
- [Portable Windows ZIP — artifact 15117052660](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45819746055/artifacts/15117052660), 65,941,537 bytes.
- [Windows installer ZIP — artifact 15116798800](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45819746055/artifacts/15116798800), 283,472,523 bytes.

### Workflows not triggered on current main

- **PAPER smoke:** not present in the exact-main check set. PR #601 changed the supervised public market-data service, installer and its tests; those paths do not match the PAPER workflow filters. PR #600 had PAPER lifecycle/safety success on its exact PR head `a808bc9d6b5d587a37cb123f44e899feae1d7ee1`, but that is not current main. This is not a failure and must not be represented as a pass on `10e26cde4eca1d83ac22c34b5d4e32e2f55a4e15`.
- **Linux connector sandbox:** not triggered by PR #601 paths. The most recent strong evidence is PR #578 exact-head run [45025054332](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45025054332), 69 tests, on `6f0c60ec3ace0091c75d3e06ecf08c459d300d5b`; it is not current-main evidence.
- **Android APK:** workflow is manual, MOBILE_APP pull-request path, or `mobile-v*` tag driven. The existing `mobile-v0.4.1` tag does not point to current main. No current-main APK artifact was found.
- **Android emulator/Maestro:** manual or MOBILE_APP/.maestro path driven; no current-main emulator evidence.
- **Shared Learning:** path-filtered to cloud/shared-learning; not triggered by these changes.

Node.js 20 deprecation warnings were emitted for GitHub Actions dependencies that are being forced onto Node.js 24. Python dependency resolution also emitted a backtracking-time warning. These are non-blocking maintenance warnings, not test failures.

## Global product readiness matrix

| Workstream | State | Verified evidence | Remaining gate |
|---|---|---|---|
| Headless backend, API and lifecycle | AMBER | Python suite and Windows EXE `/health` smoke pass on exact main | Physical start/stop/restart and long-running service validation; complete Linux product install lifecycle |
| Adaptive runtime | AMBER | Windows resource sampling, constrained-memory PAPER policy and worker resource-boundary tests pass | Actual Windows 10 target PC with about 3 GB RAM; sustained memory/CPU/concurrency and stop timing |
| PAPER engine, risk and LIVE denial | AMBER | Current-main Python tests; PAPER safety workflow passed on PR #600 exact head; invariants remain PAPER-only | Exact-main PAPER smoke not triggered by #601 paths; focused exact-main PAPER lifecycle evidence still desirable |
| Public market data / Radar | AMBER | Deferred metadata discovery, progress diagnostics, CCXT cancellation checks, supervised fixed workers, quality gates, 5 GiB storage budget and 30-day raw JSONL retention | Installed supervisor start/stop/health lifecycle; physical reconnect/freshness/endurance; metadata high-level calls can still contain multiple per-request timeouts |
| Research / synchronized L2 | AMBER | Sequence/depth quality gates, synchronized persisted L2 research, rotated-segment continuity and evidence pipeline | Reproducible chronological OOS evidence with adequate samples, costs and provenance; no profitability claim |
| Learning Vault / durable memory | AMBER | SQLite persistence foundation, restart continuity and installer SHA-256 preservation | Independent backup/restore, migrations, corruption recovery, multi-process writer safety and organization/user isolation |
| Authentication / secrets | AMBER | Local token helper, Windows DPAPI CurrentUser vault and secret-safe CI output | Rotation/revocation/onboarding review; private exchange onboarding remains outside this PAPER milestone |
| Connector sandbox / third-party execution | RED — production gate | Manifest validator, Bubblewrap builder, packaged CPython and 69-test Linux integration evidence on PR #578 exact head | Production parent/supervisor still does not launch adapter code through the manifest-backed Bubblewrap command; unsigned inventory, immutable package/TOCTOU proof, Linux egress policy and Windows filesystem/network isolation remain absent. Keep third-party connectors disabled |
| Windows installer/update/uninstall | AMBER | Exact-main install/upgrade/health/uninstall and fail-closed uninstall simulation; Vault marker preserved; artifacts available | Physical target-PC install; actual installed market-data supervisor lifecycle is not exercised end-to-end by installer smoke |
| Linux distribution | AMBER | Packaged CPython/Bubblewrap tests on PR #578 exact head | No full VST Linux installer/service install, update, health and uninstall evidence on current main |
| Android/APK and remote cockpit | AMBER / later release gate | MOBILE_APP source and APK/emulator workflows exist | No current-main APK artifact or physical device rotation/reconnect acceptance |
| LAN / remote / offline | AMBER | Local authenticated API and mobile endpoint contracts | Physical LAN/Tailscale discovery, reconnect, offline single-PC and remote identity validation |
| Virtual Office / UX | AMBER / secondary | Prototype and backend snapshot foundations exist | Verify every operational control against backend-confirmed states; visual work remains secondary |
| Documentation / release process | AMBER | Installation, market-data, connector and safety guides exist; this audit refreshes stale connector and handoff status | No formal GitHub Release, signed platform release, reproducible Linux/Android release evidence |

## Open operational issue #560 — physical target-PC acceptance

[Issue #560](https://github.com/AndreVazao/VazaoSovereignTrader/issues/560) remains open. Its latest 2026-11-26 comment states that code changes in #600 are integrated and the remaining acceptance item is a physical Windows 10 machine with approximately 3 GB RAM.

The historical target-PC evidence recorded free RAM falling from about 668 MB to 446 MB and the engine reaching about 469 MB working set. A prior stop request remained in STOPPING while the PAPER collector completed two cycles. PR #600 now moves metadata discovery into the collector worker and prevents subsequent ticker/OHLCV requests after cancellation is observed. Its documented limitation remains: CCXT timeout applies per underlying HTTP request, not as a hard wall-clock deadline for a high-level operation that may issue multiple requests. PR #601 now avoids force-killing public market-data child processes and makes uninstall fail closed unless STOPPED is confirmed.

Before any physical-PC test, perform the previously documented read-only inventory and verified SHA-256 backup of checkout, configuration, Learning Vault, artifacts and untracked files. Do not alter the target PC during this audit.

## Security and operating invariants

- PAPER-only. No LIVE activation, order execution, transfers, withdrawals or financial operations.
- No exchange credentials, private account links or financial permissions are needed for initial public-data collection.
- Fixed public workers only. Do not enable third-party connector execution until the production sandbox and platform-specific boundaries pass.
- Linux Bubblewrap network remains deny-all. Do not add broad host mounts or an unsandboxed fallback.
- Windows Job Objects are process/resource controls, not filesystem/network isolation.
- Main reports `protected=false`, rulesets are empty, and branch-protection read returned 403. No settings were changed; the repository owner must enforce mandatory review/check policy.
- A green Vercel preview is never a code test. A workflow not triggered by path filters is not a failure, but its prior result is not current-main validation.
- Never access, print or copy credentials, tokens, secrets or keys.

## Readiness estimate

- **First Windows installation on the target PC: 70–75%.** Exact-main Windows package/install/upgrade/uninstall/health CI is strong; physical low-memory acceptance and installed continuous market-data supervisor lifecycle remain.
- **Global product readiness: 58–62%.** Security sandbox production gate, Vault recovery/isolation, research OOS evidence, Linux/Android releases, remote/offline validation and release governance remain.

These ranges are engineering estimates, not measured completion percentages.

## Next engineering priorities

1. Complete the trusted Linux production supervisor/launcher integration for the manifest-backed Bubblewrap runtime with no unsandboxed fallback; authenticate and protect the runtime package, and add adversarial TOCTOU/lifecycle tests.
2. Keep third-party connectors disabled until provider egress and independent Windows filesystem/network isolation are proven.
3. Add exact-main PAPER lifecycle/safety validation where useful, without treating untriggered path-filtered runs as failures.
4. Exercise the packaged market-data supervisor start/stop/health lifecycle in Windows installer CI; preserve fail-closed uninstall.
5. Complete Learning Vault backup/restore, migration, corruption recovery and tenant isolation tests.
6. Build reproducible full Linux distribution and Android APK/emulator evidence; then test LAN/Tailscale/offline behavior.
7. Perform target-PC validation only after a read-only inventory and verified backup; no PC access was performed in this audit.
8. Configure mandatory main-branch reviews and required checks through repository settings.

**Decision:** VST is not ready to be declared globally complete. The current main SHA and exact-main CI evidence are recorded above; continue product-wide monitoring.

