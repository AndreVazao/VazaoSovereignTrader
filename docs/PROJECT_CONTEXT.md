# VAZAO SOVEREIGN TRADER — PROJECT CONTEXT & CONTINUATION PLAN

Last updated: 2026-09-30 (UTC) — current verified handoff: main at ec8eafb9d306a9146cdaeb329062fed1cc68363b; implementation PRs #258–#263 and #265–#266 merged; PR #264 documentation-only and merged
Repository: https://github.com/AndreVazao/VazaoSovereignTrader
Project: Pessoal programação
Owner's language/tone: Portuguese (Portugal), direct, collaborative; user often says “irmão”.
Purpose: durable handover for new ChatGPT conversations.

## 0. Mandatory rules

1. Read this file and verify live GitHub state before acting.
2. Continue the roadmap autonomously on safe repository/code work.
3. Always use a dedicated branch and PR; never push directly to main for normal feature work.
4. Merge autonomously when exact-head required CI is green, the PR is mergeable and review finds no blocking defect.
5. Never create Supabase/Vercel/cloud resources, deploy, incur costs, or provision real accounts without current cost/terms review and André's explicit authorization.
6. Never expose or commit passwords, tokens, keys, recovery codes, balances, private trade histories or exchange credentials.
7. Fail closed. Never bypass readiness, preflight/reconciliation, Risk Engine, RealModeGuard or PAPER/REAL gates.
8. Keep only one active implementation PR wherever practical.
9. Before finishing a session, update this context with completed work, exact branch/PR/SHA, CI outcomes, blockers and next action.

## 1. Core objective

Get VazaoSovereignTrader to a genuinely installable Windows PC state where it can run PAPER continuously, collect public market data, build its own evidence and studies, survive restarts, and only later consider REAL after all readiness and risk gates are satisfied.

Immediate operational goal: data accumulation and research, not live trading.

## 2. Current main state

PR #223 (device proof, admin approval and rate-limit hardening) was merged by André.
Current main SHA after PR #263: 648502928c0426bd86334c7f3d4957d42f4162a7.

Previous main validation before PR #263:
- Windows EXE run 36672120924: SUCCESS.
- Shared Learning Service run 36672120901: SUCCESS.
- No open PRs and no open issues at the time of this context update.
- Old branches were deleted manually by André.

PR #223 and predecessor consolidation work are complete. Do not reopen them.

## 3. Active implementation — Windows runtime + operational diagnostics

Branch: feat/paper-study-harness
Active PR will cover the reusable PAPER study harness.

Implemented:
- setup_windows.ps1 installs Python runtime, PC requirements, Playwright Chromium and persistent data directories.
- install_windows_autostart.ps1 installs two Windows Scheduled Tasks:
  - VazaoSovereignTrader for the PAPER-first engine.
  - VazaoSovereignTrader-MarketData for independent public WebSocket collection.
- Both tasks restart after failures and start at Windows boot.
- The WebSocket collector receives explicit config/data paths and resolves relative paths from repository root, preventing working-directory bugs.
- verify_pc_install.ps1 checks compilation, required imports, Playwright availability, PAPER/observational safety defaults and the full Python test suite.
- Installation/data-collection documentation was updated.
- No exchange API key is required for initial public-data collection.
- No cloud resources, deployment, account provisioning or paid service was created.

Architecture:
- The main PAPER engine already contains PaperMarketCollector for OHLCV/state/confluence/outcome evidence.
- The separate WebSocket collector adds normalized public trade tape, cross-venue lead/lag candidates and latency observations from Binance, Coinbase and OKX.
- The collectors are intentionally independent so market-data accumulation can continue if the trading engine stops.
- Neither collector submits orders or activates REAL.

## 4. Data pipeline target

public market feeds
-> normalized local tape
-> market state
-> strategies
-> confluence/evidence
-> PAPER outcomes
-> OOS/walk-forward/cost validation
-> readiness history/trend/scorecard
-> only if all gates pass, guarded REAL review

Key local artifacts:
- PC_ENGINE/data/radar/websocket_events.jsonl
- PC_ENGINE/data/radar/websocket_lead_lag.jsonl
- PC_ENGINE/data/radar/websocket_latency_edges.jsonl
- PC_ENGINE/data/radar/lead_lag_learning.json
- PC_ENGINE/data/radar/state_signature_learning.jsonl
- PC_ENGINE/data/radar/state_outcomes.jsonl
- PC_ENGINE/data/radar/evidence_ledger.jsonl
- PC_ENGINE/data/radar/readiness_history.jsonl

## 5. Existing safety architecture

Already merged:
- PAPER-first startup.
- Risk Engine.
- RealModeGuard.
- Readiness pipeline.
- Market freshness/data-quality gates.
- PAPER evidence ledger and learning.
- Champion/Challenger.
- OOS/walk-forward/regime validation.
- Financial and order reconciliation.
- Recovery state.
- Sovereign Market Radar.
- Capital Opportunity Engine.
- WebSocket lead/lag and latency evidence.
- Shared-learning service scaffold with cloud sync disabled by default.
- Device proof, admin approval and database-backed rate limits.

No verified REAL promotion has occurred. Preserve this state unless explicitly verified otherwise.

## 6. Cloud/security blockers

Still NOT AUTHORIZED:
- Supabase project creation.
- Vercel shared-learning deployment.
- Real account provisioning.
- Paid data-provider activation.

Before cloud activation:
- review current official costs/limits/terms;
- obtain explicit authorization;
- deploy only after integration/security tests;
- verify RLS, service-role grants, tenant isolation, expiry/replay/concurrency and audit behavior;
- add MFA/step-up for admin actions;
- add edge/WAF rate limiting and abuse monitoring;
- complete vault recovery, signed/versioned configuration and safe account recovery.

Cloud learning remains advisory and must never authorize REAL.

## 7. Completed since previous handover

- PR #225 merged: market-data heartbeat, exchange metrics, reconnect/error counters and authenticated `/market-data-health`.
- PR #226 merged: authenticated `/diagnostics`, latest event by venue/symbol, local storage growth metrics, deterministic JSON export and cockpit diagnostics panel.
- Exact-head CI for PR #226: Python tests SUCCESS (run 36673761535); Windows EXE SUCCESS (run 36673761420).

## 8. Active implementation — PAPER study harness

Branch: feat/paper-study-harness

Implemented:
- reusable PAPER study engine over local `market_states.jsonl`;
- net outcomes after configured costs;
- chronological OOS train/test;
- walk-forward folds;
- regime breakdown;
- deterministic Monte Carlo bootstrap;
- configurable signal vs high-confidence/high-confluence policy comparison;
- local study runner producing `paper_study_report.json`;
- unit tests and installation documentation.

Safety: research/PAPER only. No order submission, risk mutation, cloud activation or REAL promotion.

## 9. Completed research/runtime hardening

- PR #227 merged: reusable PAPER study harness with chronological OOS, walk-forward, regime analysis and Monte Carlo.
- PR #228 merged: WebSocket timestamp/latency validation gate.
- PR #229 merged: continuous PAPER studies from the market-data collector.
- PR #230 merged: fresh WebSocket timing validation required for REAL readiness; fail-closed.

## 10. Active implementation — cockpit research status

Branch: feat/cockpit-research-status

Implemented:
- authenticated `/research/status` endpoint;
- exposes PAPER study and WebSocket timing report state, age and payload;
- explicit PAPER-only/read-only semantics;
- tests and installation documentation.

## 11. Active implementation — Windows installation health report

Branch: feat/windows-installation-health-report

Implemented:
- verify_pc_install.ps1 now writes PC_ENGINE/data/logs/installation_health.json after all required verification steps pass;
- report includes runtime/config/dependency/Playwright/test status, scheduled-task state and token-presence boolean;
- report contains no secret material;
- documentation updated.

This improves deterministic post-install verification without creating cloud resources or changing execution mode.

## 11. Next actions

1. Finish/review branch feat/windows-runtime-bootstrap.
2. Open one PR for it.
3. Wait for exact-head CI: Python tests, Shared Learning Service where applicable, Windows EXE.
4. Inspect final diff and merge automatically if green and no blocking defect.
5. Verify main and CI after merge.
6. Next branch: operational self-diagnostics:
   - startup/collector health state;
   - last received market event per venue/symbol;
   - data age and feed reconnect counters;
   - local disk/data-growth monitoring;
   - authenticated cockpit status for engine + market-data collector;
   - deterministic diagnostics export.
7. Then expand the study pipeline: common PAPER harness, strategy comparison, OOS/walk-forward, Monte Carlo and regime analysis.
8. Then validate WebSocket timestamps/latency rigorously before treating lead/lag as economically meaningful.

## 12. Active implementation — REAL readiness timing gate

Branch: feat/readiness-timing-gate

Implemented:
- REAL readiness requires a fresh WebSocket timing validation report by default;
- missing, stale or failed timing validation adds `websocket_timing_validation_required` to blockers;
- timing status is exposed in readiness output;
- configuration and documentation updated.

This is an additional fail-closed gate. It does not activate REAL or bypass any existing control.

## 13. Installation target

1. Install/prepare runtime.
2. Configure local API token.
3. Run verification.
4. Install automatic startup.
5. Reboot or start the two tasks.
6. Open local dashboard/cockpit.
7. Confirm PAPER engine and market-data collector are alive.
8. Leave the PC running continuously while evidence accumulates.

No live trading account is required for this first stage.

## 14. Continuity prompt

Continue working on AndreVazao/VazaoSovereignTrader. Read this file, verify live GitHub state, then continue the active branch/PR. Work autonomously on safe code. Keep exactly one active implementation PR where practical. Merge automatically when exact-head CI is green and review finds no blocker. Do not create cloud resources or incur costs without explicit authorization. The immediate objective is a reliable installable PAPER/data-collection node that can accumulate evidence for the trader's studies while all REAL gates remain fail-closed.


## 15. Current handoff — 2026-09-30 (verified against GitHub)

### Current main
- Main SHA: `648502928c0426bd86334c7f3d4957d42f4162a7`.
- PR #260 merged at 2026-09-30 15:10 UTC; merge SHA above.
- Exact PR #260 head: `577bde3a751b7ca67b972cbe2179ec581836831b`.
- Exact-head CI for PR #260: both Python test jobs SUCCESS and Windows EXE build SUCCESS before merge.
- Repository: `AndreVazao/VazaoSovereignTrader`.

### Newly completed — venue health signage (PR #258)
- Added `PC_ENGINE/diagnostics/venue_health.py`.
- Added authenticated `GET /venue-health` endpoint.
- Cockpit displays configured venues/exchanges with GREEN / YELLOW / RED status:
  - GREEN: recent activity and minimum observation sample count met.
  - YELLOW: some data exists, but recency/sample evidence is insufficient for strong operational classification.
  - RED: no valid activity or feed is outside the operational freshness window; mark for review.
- Includes polling/WebSocket/research roles, sample counts, last activity and age.
- Added `tests/test_venue_health.py`.
- Safety: status is operational/data-quality evidence, not profitability assessment. RED never deletes/discards a venue automatically; any removal needs further review. No order submission changes.

### Newly completed — runtime evidence scorecard (PR #259)
- Added `PC_ENGINE/diagnostics/evidence_scorecard.py` runtime service.
- Added authenticated `GET /evidence-scorecard`.
- Cockpit shows presence/missing status for calibration, chronological walk-forward, regime walk-forward, cost stress and bootstrap evidence.
- Missing reports fail closed as MISSING.
- The scorecard cannot authorize REAL; `execution_authorized=false` by design.

### Newly completed — refresh PAPER evidence from cockpit (PR #260)
- Added `refresh_runtime_evidence_reports(config)` in `PC_ENGINE/diagnostics/evidence_scorecard.py`.
- Regenerates calibration, chronological walk-forward, regime walk-forward and OOS cost/bootstrap robustness reports from the completed PAPER outcomes ledger.
- Default report paths under configured radar data directory:
  - `hot_path_calibration.json`
  - `hot_path_walk_forward.json`
  - `hot_path_regime_walk_forward.json`
  - `hot_path_oos_robustness.json`
- Outcomes default path: `hot_path_outcomes.jsonl`, overridable with `radar.hot_path_outcomes_path`.
- Optional custom report paths: `radar.evidence_reports.calibration`, `walk_forward`, `regime_walk_forward`, `oos_robustness`.
- Added authenticated `POST /evidence-scorecard/refresh`.
- Cockpit has “ATUALIZAR EVIDÊNCIA PAPER” button.
- Added `tests/test_runtime_evidence_scorecard.py` and `tests/test_runtime_evidence_refresh.py`.
- If outcomes are missing, reports are generated as empty evidence artifacts; requirements remain unmet. This does not imply strategy failure; it means there is no accumulated evidence yet.
- All generated reports retain `paper_only=true`, `orders_submitted=false`, `execution_authorized=false`. No REAL gate changes and no orders are submitted.

### Historical branch / PR status at the PR #260–#261 handoff
- PR #260 was merged; no feature branch should be assumed active without checking GitHub.
- Latest completed implementation sequence: PR #258 venue health signage -> PR #259 runtime scorecard -> PR #260 explicit PAPER evidence refresh.
- PR #261 merged: updated this project context/continuation handoff. Documentation CI passed on exact head `9a6440a50f71e31d9934daa460ca7c5b4a57c1b7`; merge SHA `648502928c0426bd86334c7f3d4957d42f4162a7`.
- Before further coding, inspect live main, open PRs, and current CI. Keep one active implementation PR wherever practical.

### Immediate next engineering actions
1. Verify the documentation handoff PR and merge only if exact-head required CI is green.
2. Inspect runtime behavior/config path consistency for the evidence refresh endpoint and the venue-health source files; add/fix tests if necessary.
3. Connect venue status to richer economic evidence in later phases: latency, spread, data gaps, fee assumptions, slippage, lead/lag sample size and net PAPER outcomes. Keep operational feed health separate from profitability.
4. Ensure the runtime collector actually writes `hot_path_outcomes.jsonl` at the configured path, and that the scorecard's report paths align with the files produced in the current installation. Do not infer data exists merely because report files exist.
5. Continue accumulating PAPER-only evidence, then evaluate sample quality, OOS/walk-forward/regime stability and stressed costs. Do not claim a strategy is profitable without sufficient evidence.
6. Later create the mobile dashboard mockup as a presentation layer. User wants a polished, phone-friendly view with a clear green/yellow/red venue list and evidence/status panels. Do not let mockup work interrupt core engine hardening.
7. Never activate REAL or relax its gates. Explicit human authorization remains mandatory; no cloud deployment/spend without explicit authorization.

### User preferences and dashboard direction
- Communicate in Portuguese (Portugal), warm and direct; user calls assistant “irmão”.
- User wants autonomous progress on safe repository work and a copy/paste continuation prompt when a chat gets long.
- Dashboard should list the actual exchanges/platforms the trader is configured to use, not an invented fixed list. Green/yellow/red must be based on observed telemetry and clear rules.
- Red means “review/candidate to remove”, not automatic deletion. A healthy feed is not the same as a profitable venue; future economic classification must be separate.
- The future mobile view should include engine/PAPER state, P&L only when backed by real PAPER records, feed quality/latency, lead-lag evidence, OOS/walk-forward/regime coverage, learning status, alerts and explicit REAL LOCKED status until all gates are satisfied.

### Continuity prompt for the next chat
Continue the project `AndreVazao/VazaoSovereignTrader` in Portuguese (Portugal). First read `docs/PROJECT_CONTEXT.md` and verify live GitHub state; do not assume branches, PRs, or CI state from this note alone. Current verified main SHA at handoff: `648502928c0426bd86334c7f3d4957d42f4162a7`. PR #258 added exchange venue GREEN/YELLOW/RED operational health signage; PR #259 added a read-only PAPER evidence scorecard; PR #260 added authenticated `POST /evidence-scorecard/refresh` and a cockpit refresh button to regenerate calibration, walk-forward, regime walk-forward and OOS cost/bootstrap reports from completed PAPER outcomes. PR #260 exact-head Python test jobs and Windows EXE build all passed before merge. Continue autonomously with a dedicated branch and PR, inspect the evidence refresh path/config/collector integration, verify that outcomes are written to the same path the scorecard reads, then improve venue classification using separate operational-health and economic-performance evidence. Keep everything PAPER-only; never submit orders, activate REAL, bypass readiness/risk/RealModeGuard, create cloud resources or incur costs without explicit authorization. Merge only after exact-head required CI is green and the diff has no blockers. The user also wants a polished phone-friendly dashboard mockup later, with venue signage and trader status, but it must not interrupt core engine work.


## 16. Evidence path consistency audit — 2026-09-30

### Verified finding and fix — PR #263
- Current main after merge: `648502928c0426bd86334c7f3d4957d42f4162a7`.
- PR #263: https://github.com/AndreVazao/VazaoSovereignTrader/pull/263
- Merge commit: `648502928c0426bd86334c7f3d4957d42f4162a7`.
- Fixed a real configuration integration defect: the collector always wrote outcomes to `data_dir/hot_path_outcomes.jsonl`, even when `radar.hot_path_outcomes_path` was configured, while the refresh service read the configured override.
- Added a shared `PC_ENGINE/diagnostics/path_utils.py` resolver so relative configured paths are anchored to the repository root instead of depending on the process working directory.
- Applied consistent root-based path resolution to evidence report paths, the evidence refresh service, venue-health telemetry, and the cockpit `/market-data-health` and `/diagnostics` endpoints.
- Added tests for configured outcome path selection, relative data/report paths, and the market-data heartbeat endpoint with a relative configured data directory.
- Exact PR-head CI for `ea7d00ae5b25761f31433cc5d118887e11f2f303`: Python tests SUCCESS (run 36740419300); Windows EXE build and smoke test SUCCESS (run 36740419273). PR was mergeable/clean at merge.
- At this historical handoff, post-merge CI for `648502928c0426bd86334c7f3d4957d42f4162a7` was still running. It subsequently completed successfully on both Python tests and Windows EXE (runs 36740684028 and 36740683635).
- No changes to execution mode, Risk Engine, RealModeGuard, readiness/preflight/reconciliation, or REAL authorization. Reports remain PAPER-only; no orders were submitted and no cloud resources/costs were introduced.

### Repository housekeeping verified
- Closed stale PR #226 because its operational diagnostics endpoint/module were already present in main.
- Closed stale PR #253 because the chronological walk-forward module/tests were already present in main through later merged work.
- PR #243 remains open: `feat/lead-lag-oos-study`, head `71761c1fdc6ebfe4dd120bd32eb9d068138b8a01`. Its base SHA is old; do not merge without reviewing the diff against current main and rebasing/rebuilding its tests. Treat it as the only pre-existing feature PR, separate from the path-consistency fix.

### Next technical actions from this handoff (historical; see Section 17 for the current state)
1. Verify post-merge Python and Windows EXE CI on the exact main SHA.
2. Audit report readers/writers for corrupt UTF-8/JSON, timestamps, duplicate outcomes, insufficient samples and atomic-write recovery.
3. Harden venue-health parsing against malformed timestamps and nested telemetry structures.
4. Keep operational venue health separate from economic evidence (spread, fees, slippage, latency and PAPER lead/lag), and require sufficient sample counts.
5. Keep PAPER as the default and preserve every REAL gate. No cloud activation or spend without explicit authorization.


## 17. Current handoff — 2026-09-30, after PR #266

### Verified repository state
- Main SHA at the PR #266 handoff: `ec8eafb9d306a9146cdaeb329062fed1cc68363b` (historical; see Section 18 for current state).
- PR #264 merged: context and continuity documentation.
- PR #265 merged: defensive venue-health telemetry parsing. Merge commit `3786be983c0dcce1eabc2044b26b2102e915d710`; exact PR head `ca2d4febce1a4bba12a0919a5acdb29862223ab5`. Exact-head Python tests passed (run 36741856987) and Windows EXE build/smoke test passed (run 36741857149).
- PR #266 merged: resilient PAPER evidence ingestion and atomic report writes. Merge commit `ec8eafb9d306a9146cdaeb329062fed1cc68363b`; exact PR head `4a992b33729840ac23ee8fbd63ccd280e354c1d1`. Exact-head Python tests passed (run 36742870332) and Windows EXE build/smoke test passed (run 36742870298).
- At the time of this handoff, post-merge CI for `ec8eafb9d306a9146cdaeb329062fed1cc68363b` was still in progress. Later results and subsequent changes are recorded in Section 18.
- PR #243 was open at this historical handoff; its later review and closure are recorded in Section 18.

### PR #265 — venue health hardening
- JSONL files are read line-by-line as bytes; malformed JSON and invalid UTF-8 rows are skipped without hiding later valid rows.
- Nested snapshots/configuration and timestamps are validated defensively. Invalid/future timestamps do not count as valid recent activity or inflate the sample threshold.
- Only configured venue names are displayed. RED remains a review candidate, never an automatic deletion. Status is operational-only and does not imply profitability.

### PR #266 — PAPER evidence ingestion/report writes
- Calibration and chronological walk-forward readers now tolerate individual invalid UTF-8/JSON lines and continue processing valid records later in the ledger.
- Future timestamps are excluded from temporal calibration evidence and from chronological walk-forward records.
- Evidence scorecard loading now fails closed for malformed UTF-8/JSON, unexpected shapes and invalid/non-finite numeric fields.
- Added `PC_ENGINE/radar/report_io.py`: unique same-directory temporary file, JSON serialization, flush/fsync, then atomic replace. Failed writes clean up the temporary file and preserve the previous report. Calibration, chronological walk-forward, regime walk-forward, OOS robustness and scorecard writers use it.
- Added regression tests for corrupt input, future timestamps, malformed scorecard fields, full refresh with corrupt outcomes and preservation of prior reports after simulated replace failure.
- Safety remains unchanged: PAPER only, no order submission, no REAL promotion or gate bypass, no cloud provisioning/spend.

### Next engineering actions
1. Verify post-merge Python and Windows EXE checks for main SHA `ec8eafb9d306a9146cdaeb329062fed1cc68363b`.
2. Audit outcome identity/deduplication semantics so invalid first occurrences cannot suppress a later valid outcome with the same ID; preserve auditable duplicate/invalid counts.
3. Review PR #243 against current main. Either rebuild its per-relationship OOS study safely on a fresh branch or close it as superseded after confirming no unique useful behavior is lost.
4. Add a separate economic evidence dimension for venues (spread, fee assumptions, slippage, latency and PAPER lead/lag outcomes) only when samples are sufficient. Operational GREEN must never imply economic viability.
5. Continue PAPER accumulation and chronological OOS/regime/cost validation. Do not state profitability without adequate evidence.
6. Keep every REAL gate intact; no real orders, cloud resources, paid services or new costs without explicit authorization.


## 18. Current handoff — 2026-09-30, after PR #268

### Verified repository state
- Current main SHA immediately after PR #268 merge: `d85b75f7a7585fd8d8a71bcbd944ee151e0c5301`.
- PR #268 merged by squash: `fix: validate PAPER outcomes before deduplication`. Exact PR head: `5e0c116413a256440fcf21fa89d4e652a517faf0`; merge commit: `d85b75f7a7585fd8d8a71bcbd944ee151e0c5301`.
- Exact-head CI for PR #268 passed: Python tests run `36744031527` and Windows EXE build/smoke test run `36744031535`. The required checks `test` and `build-exe` were both completed/successful on the exact head SHA before merge.
- Post-merge Python and Windows EXE workflows for main SHA `d85b75f7a7585fd8d8a71bcbd944ee151e0c5301` were still queued/in progress at the last check (runs `36744277691` and `36744277832`). Verify both before declaring post-merge validation complete.
- No open PRs were present immediately after the merge. PR #243 was closed unmerged after review; its remote branch remains intact.

### PR #268 — outcome deduplication correctness
- Fixed a calibration bug where the first record reserved its identity before validation. An invalid/incomplete first occurrence could therefore suppress a later valid PAPER outcome sharing the same `outcome_id`.
- Required fields and finite metrics are now checked before reserving the identity. Invalid rows remain accounted for as invalid, while valid duplicates continue to be deduplicated.
- Added regression coverage for invalid-first / valid-later records with the same explicit identity. The valid row contributes to calibration; invalid and duplicate counters remain auditable.
- No changes to execution behavior, REAL gates, Risk Engine, RealModeGuard or order submission.

### PR #243 review outcome
- PR #243 (`feat: add chronological OOS study for lead-lag outcomes`) was reviewed against the hardened evidence pipeline and closed unmerged.
- Reason: the collector integration performs a full JSONL read/study (up to 100,000 records) inside `on_market_event`, potentially repeating heavy work on every market event and interfering with feed processing. Its UTF-8 text-mode loader also does not tolerate invalid UTF-8, unlike the hardened evidence readers.
- The per-relationship OOS analysis may still be useful. Rebuild it later on a fresh branch, based on current main, with robust line-by-line parsing, bounded/explicit refresh cadence, atomic report writes, chronological holdout and no REAL authorization. The closed PR's branch is retained as reference.

### Next engineering actions
1. Verify post-merge Python and Windows EXE runs `36744277691` and `36744277832` for main SHA `d85b75f7a7585fd8d8a71bcbd944ee151e0c5301`.
2. Rebuild per-relationship lead/lag OOS analysis safely, outside the per-market-event callback. Prefer integrating it with the explicit PAPER evidence refresh/report pipeline.
3. Continue the separate venue economic-evidence dimension (spread, fee assumptions, slippage, latency and PAPER lead/lag) only with adequate samples; operational GREEN must never imply economic viability.
4. Continue PAPER accumulation, chronological OOS/regime validation and stress-cost analysis. Do not claim profitability without sufficient evidence.
5. Preserve PAPER as default and every REAL gate. No real orders, cloud resources, paid services, secrets or new costs without explicit authorization.


## 19. Handoff — 2026-09-30, after PR #270

### Verified repository state
- Current main SHA after squash merge: `3cbd636aae75ffdaea232535dcdec4ecab46679e`.
- PR #270 (`feat: add relationship-level PAPER OOS evidence`) merged from exact head `1c61100db7cdfbf3540f1ce705a1edb88caf029f`; merge commit `3cbd636aae75ffdaea232535dcdec4ecab46679e`.
- Before merge, exact-head checks were green: Python test runs `36745730764` and `36745722415`, and Windows EXE build/smoke run `36745730758`. All reported success on the exact PR head SHA.
- Post-merge validation for main SHA `3cbd636aae75ffdaea232535dcdec4ecab46679e` is pending: Python run `36745981889` is in progress; Windows EXE run `36745981965` is queued. Verify both before declaring main fully validated.
- No open PRs were present immediately after the merge.

### PR #270 — per-relationship chronological OOS
- Added `PC_ENGINE/radar/hot_path_relationship_oos.py`, invoked only through the explicit evidence-refresh/report pipeline; no full JSONL study is run in `on_market_event`.
- Reads completed PAPER outcomes only (`status=COMPLETED`, `paper_only=true`, `orders_submitted=false`), validates finite metrics and timestamps, rejects future timestamps, tolerates malformed UTF-8/JSON lines, and deduplicates only after validating records.
- Produces a per-`symbol/leader/follower/direction/horizon` chronological train/test holdout, avoiding splits across equal timestamps. Reports sample sufficiency, means, median, positive rate, data-integrity counters and atomic JSON output.
- OOS intervals use deterministic moving-block bootstrap (minimum 500 replicates; unavailable below 8 test samples) rather than an IID normal approximation. Positive lower bound is only a candidate for further PAPER review, never a profitability guarantee or execution authorization.
- Integrated with `refresh_runtime_evidence_reports`, configurable `evidence_reports.relationship_oos` path, and the evidence scorecard. Missing/invalid reports remain fail-closed; `execution_authorized=false`, `paper_only=true`, and `orders_submitted=false`.
- Tests cover chronological splitting, equal-timestamp boundaries, corrupt input, invalid-first deduplication, sample thresholds, atomic report writes, configured paths and scorecard evidence presence. No changes to REAL gates, RealModeGuard, Risk Engine, preflight, reconciliation or order submission.

### Next engineering actions
1. Verify post-merge Python run `36745981889` and Windows EXE run `36745981965` for the exact main SHA above.
2. Continue the venue economic-evidence dimension separately from operational health: only configured/observed venues, and only enough PAPER samples for spreads, fees, slippage and lead/lag. GREEN operational health must not imply economic viability.
3. Add/verify an end-to-end path test from collector append to explicit refresh output using the same configured relative and absolute `hot_path_outcomes_path`; keep all expensive report generation out of market-event callbacks.
4. Continue chronological OOS, regime stratification and cost-stress accumulation. Do not declare profitability without adequate evidence.
5. Keep PAPER as default. Never submit live orders, enable REAL or bypass any gate. No paid/cloud resources or costs without explicit approval.


## 20. Handoff — 2026-09-30, after PR #272

### Verified repository state
- Current main SHA immediately after PR #272 merge: `64239b5fbd4b03c19ab98c592b7393d82d596c67`.
- PR #272 (`test: verify PAPER outcome path end to end`) merged by squash from exact head `7486bb47a655068864a0b137a6c4bb3086ea79b0`; merge commit `64239b5fbd4b03c19ab98c592b7393d82d596c67`.
- Exact-head Python test run `36746374511` passed.
- Post-merge main CI is pending at handoff: Python run `36746526064` is queued and Windows EXE run `36746526009` is in progress. Verify both against main SHA `64239b5fbd4b03c19ab98c592b7393d82d596c67`.
- No open PRs were present immediately after merge.

### PR #272 — collector-to-refresh path integration
- Added an end-to-end test using the same configured relative `hot_path_outcomes_path` for the collector's path resolver and the evidence refresh resolver.
- The test writes completed PAPER outcomes through the real `append_paper_outcomes` persistence function, invokes the explicit report refresh, and verifies the relationship OOS report consumed the exact same file and was written under the configured data directory.
- Both collector and refresh roots are isolated to a temporary directory; no production files or external services are touched. Execution authorization remains false.
- This complements the prior unit tests for relative/absolute path resolution and report generation. It does not move report generation into market-event callbacks.

### Next engineering action
- After post-merge CI is green, implement the separate venue economic-evidence dimension without conflating it with operational health. Use only configured/observed venues and adequately sampled PAPER data; include spreads, explicit fee assumptions, slippage, latency and relationship-level OOS evidence. No fabricated venue lists, no economic GREEN from health-only signals, and RED means review rather than automatic removal.
- Continue to preserve PAPER default, RealModeGuard, readiness/preflight, reconciliation, Risk Engine and all execution gates. No live orders, paid/cloud resources, secrets or costs without explicit approval.
