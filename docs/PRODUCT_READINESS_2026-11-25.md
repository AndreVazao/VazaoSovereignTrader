# VST global product readiness — 2026-11-25

**Repository:** AndreVazao/VazaoSovereignTrader only  
**Audited main code baseline:** 3a99410cb4ccb9ff43add3c42551f64bdb67d66f  
**Latest code integration:** PR #595, merged 2026-11-25 07:06:36 UTC  
**Audit boundary:** GitHub source, Actions, workflow definitions, current documentation and exact commit metadata. No credentials, private exchange accounts or financial actions were accessed.

## Executive assessment

The repository has made measurable progress in public market-data integrity, synchronized L2 research, collector supervision, bounded persistence and Windows installer validation. The exact current main SHA passes the Python suite and Windows EXE/installer workflow.

**VST is not globally complete and is not yet physically validated on the target PC.** The current evidence supports a CI-validated Windows package, not a production-ready 24/7 deployment. The open low-resource shutdown issue, missing physical-PC evidence, incomplete production connector sandbox integration, partial durable-learning rollout and absent exact-main Android/Linux release evidence remain material gaps.

Keep the product PAPER-only. Public market-data collection requires no exchange credentials. Do not enable LIVE, private account ingestion or third-party connectors.

## Repository inventory

- Default branch: main.
- Main SHA: 3a99410cb4ccb9ff43add3c42551f64bdb67d66f.
- Open pull requests: 0 at the audit time.
- Branch refs: 52 total, including main. Several feature/fix/docs branches are retained after squash merges or have diverged from current main; compare each head with main before reuse. No branch is designated as the active reviewed delivery line while there are no open PRs.
- Recent merged code: #593 OKX public WebSocket application heartbeat; #594 incomplete trailing JSONL recovery; #595 periodic raw-data retention including rotated JSONL backups. Earlier current-main work includes synchronized L2 quality/research and scheduled PAPER evidence refresh.
- Formal GitHub Releases: none.
- Tag inventory: mobile-v0.4.1 is present at 8a5a54b45b3a8358c136efc0615b088a305f4ef7; it does not point to the audited main SHA.
- Main governance: the branch endpoint reports protected=false and protection.enabled=false; repository rulesets endpoint returns an empty list. Required checks/reviews are therefore not enforced by branch protection or rulesets at this audit time. No repository settings were changed.

Useful links:
- Repository: https://github.com/AndreVazao/VazaoSovereignTrader
- Main commit: https://github.com/AndreVazao/VazaoSovereignTrader/commit/3a99410cb4ccb9ff43add3c42551f64bdb67d66f
- Pull requests: https://github.com/AndreVazao/VazaoSovereignTrader/pulls
- Branches: https://github.com/AndreVazao/VazaoSovereignTrader/branches
- Releases: https://github.com/AndreVazao/VazaoSovereignTrader/releases

## Exact-SHA CI evidence

### Current main SHA: 3a99410cb4ccb9ff43add3c42551f64bdb67d66f

- Python tests: [run 45565585331](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45565585331) — success. Job log: 1,707 passed, 4 skipped, 101 subtests passed in 54.43 seconds.
- Windows EXE: [run 45565585173](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45565585173) — success. Both build-exe and build-installer jobs passed.
- Windows EXE job covered PowerShell helper syntax, Windows PowerShell 5.1 token-helper generation/preservation/weak-token rejection, DPAPI credential-vault tests, constrained-memory PAPER resource-policy tests, connector worker resource-boundary tests, resource sampling, EXE build and HTTP /health smoke.
- Windows installer job passed silent previous-version install, in-place upgrade, installed-engine and worker-file checks, manual-first/no-autostart assertions, engine launch and HTTP health, silent uninstall, and Learning Vault marker SHA-256 preservation.
- Current-main Actions artifacts from run 45565585173:
  - Installer ZIP artifact 15000113809, 283,487,036 bytes: https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45565585173/artifacts/15000113809
  - Portable Windows ZIP artifact 14999812593, 65,938,083 bytes: https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45565585173/artifacts/14999812593
- The combined commit-status endpoint surfaced only a Vercel success status. Vercel is not a code test. No Snyk result surfaced in the current exact-SHA Actions/status evidence.

### Relevant workflows not triggered on this SHA

- Trading engine PAPER smoke: latest main pass is [run 45183259176](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45183259176) on SHA d39361fbeaef16c856a6e420def846fe1e5948aa, not current main. The #594/#595 changed paths do not match this workflow's configured filters. This is not a failure and must not be represented as a pass on current main.
- Connector sandbox Linux: latest main pass is [run 45421373097](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45421373097) on SHA aab7d749c0d52acff234461cffb775002aca0d1e, not current main. Its paths were not changed by #590–#595. This is not a failure and is not exact-main validation.
- Android APK: workflow is manual, MOBILE_APP pull-request path, or mobile-v* tag driven; no current-main APK build was found. The Android emulator/MAESTRO smoke is manual or MOBILE_APP pull-request driven, not a main push workflow.
- Shared Learning Service: path-filtered to cloud/shared-learning; not triggered by the current changes.
- PAPER smoke is only required when its configured paths trigger it. Its absence on #594/#595 is not a failure.

## Product readiness matrix

| Workstream | State | Evidence on repository | Remaining validation / next step |
|---|---|---|---|
| Headless brain, API and lifecycle | AMBER | PC_ENGINE, local authenticated API, engine health endpoint; full Python suite passes; Windows EXE health smoke passes on exact main | Physical install/start/stop/restart and long-running operation on target PC |
| Adaptive runtime and resource profiles | AMBER | CPU/RAM/disk sampling, adaptive resource manager and constrained-memory PAPER policy tests run in Windows CI | Validate actual Compact profile and shutdown behavior on the approximately 3 GB RAM target machine |
| PAPER engine, risk and LIVE denial | AMBER | PAPER invariants, risk authorization, recovery and financial-order tests exist; configuration remains PAPER-only | Current-main PAPER smoke not triggered by #594/#595; run focused PAPER lifecycle/safety validation on an exact current-main SHA |
| Public market data and connectors | AMBER | REST/WebSocket collectors, reviewed venue catalogue, top-of-book/L2 quality gates, OKX heartbeat, supervised workers, 5 GiB aggregate budget and 30-day retention | Physical venue connectivity, freshness, reconnect, bounded stop and sustained collection; installer CI verifies worker files but does not start the installed supervisor |
| Research and market analysis | AMBER | Synchronized L2 depth research consumes persisted books; bounded JSONL reads, sequence checks and rotated-segment continuity fixes are in main | Reproducible chronological OOS evidence with costs and sufficient sample quality; no profitability claim |
| Learning Vault and durable memory | AMBER | Owner-private SQLite first consumer, runtime diagnostics, restart continuity tests; installer CI verifies Vault marker bytes across upgrade/uninstall | Backup/restore to a separate destination, broader department adoption, multi-process writer/recovery and organization/user isolation acceptance |
| Authentication and secrets | AMBER | Local VST token helper and Windows DPAPI CurrentUser vault tests pass in Windows CI; no secret values logged by the workflow | Secure onboarding/rotation/revocation review; no private account onboarding is part of the current PAPER milestone |
| Connector sandbox/security | AMBER — production gate | Linux Bubblewrap manifest/runtime foundation and isolated-worker tests exist; latest Linux sandbox run passed on an earlier SHA | Production supervisor is not yet wired to the strict manifest-backed launch path; Windows filesystem/network isolation and provider egress controls are incomplete. Keep third-party connectors disabled |
| Windows installer/update/uninstall | AMBER | Exact-main installer CI passed silent install, in-place upgrade, engine health, uninstall and Vault preservation; artifacts exist | Physical target-PC validation; add packaged market-data supervisor start/stop/health lifecycle coverage |
| Linux distribution/runtime | AMBER | Python tests run on Ubuntu; Linux sandbox workflow has a previous-main pass | No current-main Linux install package or end-to-end local installation evidence |
| Android/APK and remote cockpit | AMBER / later release gate | MOBILE_APP source, endpoint/startup contract tests and APK/emulator workflows exist | No exact-main APK artifact or current-main emulator evidence; build and test from a reviewed mobile tag/PR before declaring Android ready |
| LAN/remote/offline integration | AMBER | Local API, Android cockpit contracts and operator file exchange exist; docs prohibit router port-forwarding and defer remote access to authenticated private networking | Physical LAN/Tailscale pairing, reconnect, identity and offline single-PC validation |
| Virtual Office / UX | AMBER / secondary | Prototype and mobile UI code exist; API contracts are documented | Verify backend-connected controls against stable authenticated contracts; do not let visual work delay critical runtime/security fixes |
| Documentation and release process | AMBER | Installation, PAPER safety, market-data, runtime and platform guides exist | PROJECT_CONTEXT handoff was stale at the audited SHA; this refresh corrects the handoff. No formal GitHub release exists |

## Open operational blocker: issue #560

[Issue #560](https://github.com/AndreVazao/VazaoSovereignTrader/issues/560) remains open. It records the approximately 3 GB RAM target-PC case where stop previously remained in STOPPING while the PAPER collector completed network polling.

Current main now contains bounded public-request timeouts (default 8 seconds, clamped 1–60 seconds), cooperative stop checks between venue/symbol requests, a bounded collector shutdown wait (default 10 seconds), and tests that retain live worker references after a shutdown timeout rather than force-killing them. These are meaningful code fixes, but the issue's physical constrained-Windows acceptance is not proven by hosted CI. Keep the issue open until target-PC evidence shows bounded stop, clean restart, healthy persistence and stable resource use.

## Important remaining gates

1. Physical Windows validation on the intended low-resource PC: install, configure PAPER, start engine and market-data supervisor, verify health/freshness, run bounded and sustained collection, stop cooperatively, restart, and confirm Vault/data retention.
2. Add a packaged-installer integration test that starts and stops the installed market-data supervisor and validates its health/worker recovery. Current installer lifecycle CI checks worker binaries are present but only launches the engine for HTTP health.
3. Complete production connector-supervisor integration with manifest-backed Linux sandbox execution; retain fail-closed behavior and keep third-party connectors disabled until Windows filesystem/network isolation and provider egress controls are independently tested.
4. Complete Learning Vault backup/restore, multi-process recovery and owner/organization isolation acceptance.
5. Run Android APK build and emulator UI smoke on a reviewed exact SHA; publish a versioned artifact only after checks pass.
6. Decide and enforce branch protection/rulesets at repository level so applicable checks and review requirements cannot be bypassed accidentally.
7. Keep private account onboarding separate and disabled. No exchange credentials or private accounts are required for first public-data/PAPER installation.

## Release decision

**Not ready for a global completion declaration.** Current main is CI-validated for Python and Windows EXE/installer. First PC installation remains pending physical validation and installed collector-supervisor lifecycle evidence. Global product completion additionally requires the security, Vault, data, PAPER, platform and integration gates above. Do not infer readiness from a green PR, one installer artifact, or a Vercel preview.

---

