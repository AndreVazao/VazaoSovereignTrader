# VAZAO SOVEREIGN TRADER — PROJECT CONTEXT & CONTINUATION PLAN

Last updated: 2026-10-02 (UTC) — PR #316 merged as 43eba2a94dd490e89b997300a422a8b7e62c15b0; PR #317 open on feat/opportunity-registry-schema; exact-head CI pending after latest safety test
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

## 21. Handoff — 2026-09-30, after PR #273 and venue economics implementation start

### Verified repository state
- PR #273 (documentation handoff after collector-to-refresh integration) merged by squash. Exact head `1681d3e821f7ed2d33edaecda29cfdcf569bc5cd`; merge commit `dc653064a5f91a34f54d12f959d2f361eb1db89e`.
- Exact-head Python tests passed for PR #273 (run `36746595551`).
- Before PR #273 merge, post-merge CI for parent main SHA `64239b5fbd4b03c19ab98c592b7393d82d596c67` completed successfully: Python run `36746526064`, Windows EXE build/smoke run `36746526009`.
- New post-merge CI for main SHA `dc653064a5f91a34f54d12f959d2f361eb1db89e` started as runs `36749711224` (Python) and `36749711208` (Windows EXE); verify final conclusions before treating the new main SHA as validated.
- Implementation branch `feat/venue-economic-evidence` started from this main SHA. The feature is not yet merged; continue with one PR and exact-head checks.

### Venue economic evidence — implementation in progress
- Added `PC_ENGINE/diagnostics/venue_economic_evidence.py`, a cold-path report built from completed PAPER outcomes only. It groups observed outcomes by configured follower venue, validates status/PAPER flags/finite net outcome/timestamps, rejects future records, tolerates malformed UTF-8/JSON lines, deduplicates, and emits integrity counters.
- The report distinguishes insufficient samples, non-positive chronological holdout mean, and a positive holdout mean that is only a review candidate. It records observed PAPER cost assumptions (fees, slippage, latency penalty) and explicitly marks spread as unavailable until valid bid/ask evidence exists.
- Integrated the report into explicit `refresh_runtime_evidence_reports` output with configurable `evidence_reports.venue_economic_evidence` path, `venue_economics_min_samples`, `venue_economics_min_oos_samples`, and `venue_economics_max_records`. This is intentionally not a REAL readiness gate or authorization signal.
- Tests added for configured venues only, positive/non-positive holdout behavior, insufficient samples, corrupt/future/non-PAPER inputs, cost summaries and refresh integration. Await CI to validate.
- No Supabase/Vercel resource, cloud deployment, paid service, credential, real order, or new spend was created.

### Next actions
1. Inspect the feature diff and verify Python tests and Windows EXE build/smoke test on the exact PR head SHA.
2. Fix any failing checks/review issues; merge only when required exact-head checks are green and the PR is clean/mergeable.
3. Verify post-merge Python and Windows EXE checks on the new main SHA.
4. Later, consider actual bid/ask spread evidence only if the collectors can record reliable bid/ask snapshots. Do not infer spread from trade prints.
5. Keep operational venue health separate from economic evidence. GREEN means operationally active, not profitable; a positive holdout mean is only a research candidate, never a promotion or execution authorization.
6. Preserve PAPER defaults, RealModeGuard, readiness/preflight, reconciliation, Risk Engine and all REAL gates. No cloud provisioning or costs without explicit authorization.

## 22. Handoff — 2026-09-30, after PR #274 venue economic evidence

### Verified repository state
- PR #274 (`feat: add separate PAPER venue economic evidence`) merged by squash. Exact PR head `8d3396250b26c9de2e43f7160079a21c33c50050`; merge commit/main SHA `f288905b229e9c24b1c9d64ddb936ce841c9c49c`.
- Exact-head PR checks passed on SHA `8d3396250b26c9de2e43f7160079a21c33c50050`: Python tests run `36750471740` and Windows EXE build/smoke run `36750471811`. Both required checks concluded success and PR was clean/mergeable before squash merge.
- Post-merge CI for main SHA `f288905b229e9c24b1c9d64ddb936ce841c9c49c` was started as Python run `36750719099` and Windows EXE run `36750719613`; verify both before declaring this main SHA fully validated.
- No open PRs immediately after PR #274 merge; documentation handoff branch `docs/handoff-after-venue-economics` is now being used to update this context.

### PR #274 — PAPER venue economic evidence
- Added `PC_ENGINE/diagnostics/venue_economic_evidence.py`, a cold-path report from completed PAPER outcomes, grouped by configured follower venue. Validates PAPER flags, finite realized net outcomes and timestamps, rejects future timestamps, tolerates corrupt UTF-8/JSON lines, deduplicates, and reports integrity counters.
- Reports sample sufficiency, chronological holdout mean/positive rate, and recorded fees/slippage/latency assumptions. A positive holdout mean is only `POSITIVE_OOS_CANDIDATE`, not proof of profitability or permission to trade; non-positive holdout and insufficient data remain explicit.
- Spread is deliberately `UNAVAILABLE_NO_BID_ASK_EVIDENCE`: the current trade-print feed does not provide trustworthy bid/ask snapshots, so no spread estimate is fabricated.
- Integrated with explicit `refresh_runtime_evidence_reports`; configurable report path `evidence_reports.venue_economic_evidence`, `venue_economics_min_samples`, `venue_economics_min_oos_samples`, and `venue_economics_max_records`. The loader retains a bounded set of valid outcomes and records evictions.
- Unit/integration tests cover configured venues only, cost summaries, positive/non-positive holdout, insufficient data, corrupted/future/non-PAPER records, and report generation. Exact-head CI passed.
- Economic evidence is separate from operational health and does not feed REAL readiness or authorize execution. PAPER only, `orders_submitted=false`, `execution_authorized=false`.

### Next engineering actions
1. Verify post-merge Python and Windows EXE checks for main SHA `f288905b229e9c24b1c9d64ddb936ce841c9c49c`.
2. Add the new venue economics report to the dashboard as a separate panel next to operational venue health, preserving the existing green/yellow/red operational signal and showing economic sample sufficiency independently.
3. Only add measured spread metrics after collectors reliably capture timestamped bid/ask data; never infer spread from trade prints.
4. Keep GREEN operational health distinct from profitability; positive OOS means candidate for further PAPER review only, never automatic venue promotion/removal or execution authorization.
5. Preserve PAPER defaults and every REAL gate. No Supabase/Vercel resources, deployments, paid services, credentials, live orders or costs without explicit authorization.

## 23. Handoff — 2026-09-30, dashboard venue economics integration in progress

### Verified baseline
- PR #275 (documentation handoff after PR #274) merged by squash with merge commit `d44c67f875df4c7d88d39389c10825da52f64551`.
- PR #274 venue economic evidence is merged. Its exact-head Python and Windows EXE checks passed; post-merge Python and Windows EXE checks on `f288905b229e9c24b1c9d64ddb936ce841c9c49c` both completed successfully.
- Feature branch `feat/dashboard-venue-economics` was created from the verified main after PR #275.

### Dashboard integration — implementation in progress
- Added authenticated read-only `GET /venue-economic-evidence`, which reads the configured `evidence_reports.venue_economic_evidence` file (or the default report path), returns `NOT_STARTED` when absent, and fails closed if the report is malformed or its PAPER/order/execution safety flags do not match expected invariants.
- Added a separate cockpit panel for PAPER venue economics, distinct from the operational GREEN/YELLOW/RED signal. It displays outcome/OOS sample counts, holdout net mean and recorded fee/slippage/latency assumptions. Positive OOS evidence is labelled as a candidate for review, never green/approved; spread is explicitly unavailable without bid/ask data.
- The existing explicit PAPER evidence refresh now reloads the economic panel. The panel is also read-only on page load; it does not trigger heavy report generation automatically.
- Added authenticated endpoint tests for missing token, configured report paths and fail-closed safety invariant validation. Python/Windows CI still needs to validate the exact PR head.
- No changes to trading execution, REAL readiness gates, RealModeGuard, Risk Engine, preflight or reconciliation. No Supabase/Vercel provisioning, deployment, spend, credentials or real orders.

### Next actions
1. Inspect the final diff, wait for exact-head Python and Windows EXE build/smoke checks, and fix any issues before merging.
2. Verify post-merge Python and Windows EXE checks on the new main SHA.
3. Keep economic signals separate from operational health and execution authorization. Do not estimate spread from trade prints.
4. Continue only with safe PAPER evidence improvements; do not provision cloud resources or incur costs without explicit authorization.

## 24. Handoff — 2026-09-30, after dashboard venue economics integration

### Verified repository state
- PR #276 (`feat: show venue economic evidence in dashboard`) merged by squash. Exact PR head `9ac706a26c446f68f008f2cb2145abdd31ae54e1`; merge commit/main SHA `6b5794c5ac4b770d9da5de44b159715766a0d28e`.
- Exact-head PR checks passed on `9ac706a26c446f68f008f2cb2145abdd31ae54e1`: Python tests run `36751325469` and Windows EXE build/smoke run `36751325456`.
- Post-merge CI for main SHA `6b5794c5ac4b770d9da5de44b159715766a0d28e` is running as Python run `36751581750` and Windows EXE run `36751581645`. Verify both before declaring this SHA fully validated.
- No open PRs were present immediately after PR #276 merge. The handoff update is being made on branch `docs/handoff-after-dashboard-economics`.

### PR #276 — dashboard economic panel
- Added authenticated, read-only `GET /venue-economic-evidence`; it reads the configured report path, returns `NOT_STARTED` when absent and returns 409 with fail-closed flags for malformed reports or invalid safety invariants.
- Added a separate cockpit panel for PAPER economics beside operational venue health. It shows sample counts, chronological holdout net mean and recorded fee/slippage/latency assumptions. Positive holdout mean is amber/review-candidate only; non-positive holdout is distinct from insufficient samples. No economic status is treated as operational GREEN or REAL authorization.
- The existing explicit PAPER evidence refresh refreshes the economic panel. Page load only reads the existing report and does not trigger expensive report generation.
- Endpoint tests cover authentication, configured relative report paths and rejection of invalid execution safety flags. Exact-head Python and Windows EXE checks passed.
- No trading behavior or REAL gates changed; no cloud resources, deployment, paid services, secrets or live orders were created.

### Next engineering actions
1. Verify post-merge Python and Windows EXE runs `36751581750` and `36751581645` on the exact main SHA above.
2. Next research improvement: only implement spread evidence if public collectors can capture valid timestamped bid/ask snapshots; trade prints alone are not enough.
3. Continue accumulating PAPER outcomes and require sufficient chronological OOS evidence before interpreting venue economics. Positive mean remains a candidate for review, not proof of profitability.
4. Keep operational status, economic evidence and REAL authorization as three separate concepts. Preserve all gates and do not provision Supabase/Vercel resources or incur costs without explicit authorization.

## 25. Handoff — 2026-09-30, after PR #277

### Verified repository state
- PR #277 (documentation handoff after dashboard venue economics integration) merged by squash; merge commit/main SHA `373b3ca588a6f2a0f2421d266600d0ceeb4b401d`.
- PR #276 dashboard integration exact-head checks passed: Python run `36751325469`, Windows EXE run `36751325456` on head `9ac706a26c446f68f008f2cb2145abdd31ae54e1`.
- Post-merge Python and Windows EXE checks for parent main SHA `6b5794c5ac4b770d9da5de44b159715766a0d28e` both succeeded (runs `36751581750` and `36751581645`).
- Current main SHA `373b3ca588a6f2a0f2421d266600d0ceeb4b401d` post-merge Python run `36751831415` and Windows EXE run `36751831289` are in progress; verify both before declaring current main fully validated.
- No open PRs were present immediately after PR #277 merge. This context refresh is on branch `docs/handoff-after-dashboard-panel`.

### Current product behavior
- The dashboard now shows operational venue health and PAPER venue economics in separate panels. The economics panel reads the report through authenticated GET `/venue-economic-evidence`; it does not refresh expensive reports on page load.
- The explicit PAPER evidence refresh regenerates the venue economic report and reloads the panel. Positive chronological holdout mean remains a review candidate only; insufficient samples and non-positive holdout are separately labelled.
- Spread remains unavailable until reliable timestamped bid/ask observations are collected. No trade-print-derived spread estimates are allowed.
- No changes to execution or REAL gates. No cloud resources, deployments, paid services, credentials or live orders.

### Next action
- Verify current main post-merge CI. Then evaluate whether a separately tested public bid/ask collector can safely gather top-of-book snapshots with freshness, rate-limit, reconnect and timestamp integrity controls. Do not conflate operational status, economic evidence or REAL authorization.

## 25. Handoff — 2026-09-30, bootstrap uncertainty for venue economic evidence

### Verified state
- PR #276 dashboard economic panel merged at `6b5794c5ac4b770d9da5de44b159715766a0d28e`; its exact-head Python and Windows EXE checks passed.
- PR #277 documentation handoff merged at `373b3ca588a6f2a0f2421d266600d0ceeb4b401d`; post-merge Python and Windows EXE checks both passed on that SHA (`36751831415`, `36751831289`).
- PR #278 documentation handoff merged at `fd02f7954628649571cd32cdee0918fed00f5988`. Post-merge Python run `36752233265` passed; Windows EXE run `36752233112` was still in progress at the last check. Verify its final conclusion.
- Current feature branch `feat/venue-oos-bootstrap-uncertainty` was created from `fd02f7954628649571cd32cdee0918fed00f5988`.

### Venue economics confidence intervals — implementation in progress
- The prior report called a positive chronological holdout mean a candidate even when the OOS sample was too small to estimate uncertainty. This change adds a deterministic moving-block bootstrap 95% interval, preserving short-range chronological dependence; fewer than 8 OOS observations yields an unavailable interval.
- `POSITIVE_OOS_CANDIDATE` now requires the interval's lower bound to be above zero. `NON_POSITIVE_OOS` requires the upper bound below zero. Intervals spanning zero become `UNCERTAIN_OOS`; too few OOS observations become `INSUFFICIENT_OOS_FOR_CI`.
- The dashboard panel is being updated to show the interval and distinguish uncertain evidence from non-positive or insufficient evidence. None of these statuses changes operational venue health or authorizes execution.
- Tests cover positive supported evidence, negative holdout, mixed/uncertain holdout, and too-small samples. Exact-head CI is not yet validated.

### Next actions
1. Verify the main Windows EXE run `36752233112` for SHA `fd02f7954628649571cd32cdee0918fed00f5988`.
2. Finish reviewing the feature diff and run exact-head Python tests plus Windows EXE build/smoke checks.
3. Merge only after all required checks succeed on the exact PR head and the PR is clean/mergeable; then verify post-merge CI.
4. Continue to keep PAPER evidence, operational health, and REAL authorization independent. Spread stays unavailable until valid timestamped bid/ask observations are actually collected and validated.

## 26. Handoff — 2026-09-30, venue OOS bootstrap uncertainty merged

### Verified repository state
- PR #279 (`feat: add bootstrap uncertainty to venue economics`) merged by squash. Exact PR head `d83438d1bb04d1e1951bf45ed7cd3d88e0e40329`; merge commit/main SHA `0e64d31fb805f92f8bd866720c1e10ee096342be`.
- Exact-head checks passed on PR #279 SHA: Python tests run `36752698057` and Windows EXE build/smoke run `36752697940`; PR was clean/mergeable before merge.
- Post-merge Python run `36752997010` and Windows EXE run `36752997208` were still in progress at handoff creation. Verify final conclusions before declaring this main SHA fully validated.
- No open PRs immediately after PR #279 merge. Documentation branch `docs/handoff-after-venue-oos-bootstrap` is being used to capture this handoff.

### PR #279 — more conservative venue economic evidence
- Venue economic evidence now computes a deterministic moving-block bootstrap 95% interval over chronological OOS PAPER outcomes, preserving short-range temporal dependence. Fewer than 8 OOS samples means the interval is unavailable.
- `POSITIVE_OOS_CANDIDATE` now requires the 95% interval lower bound to be above zero; `NON_POSITIVE_OOS` requires the upper bound below zero; an interval crossing zero is `UNCERTAIN_OOS`; too few OOS samples is `INSUFFICIENT_OOS_FOR_CI`.
- The dashboard shows the interval and distinguishes uncertain from non-positive or insufficient evidence. Even a positive supported interval is a candidate for further PAPER review only, never an execution or venue-promotion signal.
- Tests cover positive supported evidence, negative holdout, mixed/uncertain holdout, and insufficient OOS samples. Exact-head Python and Windows EXE checks passed.

### Next engineering actions
1. Verify post-merge Python and Windows EXE checks for main SHA `0e64d31fb805f92f8bd866720c1e10ee096342be`.
2. Research reliable top-of-book evidence before implementing spread reporting. `PC_ENGINE/market_events/websocket_collectors.py` parses bid/ask ticker observations for Binance, OKX and Coinbase, but the default `run_market_data_collector.py` currently uses the trade-only `WebSocketMarketRadar`. The separate L2 collector persists snapshots/deltas; deltas must not be mistaken for full book snapshots without stateful book reconstruction.
3. If implementing spread collection, use public ticker/top-of-book observations with venue/symbol, valid positive bid/ask, bid < ask, exchange/provider timestamp and local receive timestamp; cap/rotate persistence, tolerate corrupt lines, and report freshness/sample sufficiency. Do not change trade callback latency or introduce orders.
4. Keep operational health, economic evidence and REAL authorization separate. Preserve PAPER defaults and all existing gates. No Supabase/Vercel provisioning, deployments, paid services, credentials, live orders or spend without explicit authorization.

## 27. Handoff — 2026-09-30, public top-of-book spread evidence in progress

### Baseline
- PR #279 added deterministic moving-block bootstrap intervals for venue PAPER OOS evidence and was merged at `0e64d31fb805f92f8bd866720c1e10ee096342be`; exact-head Python and Windows EXE checks passed, and post-merge Python/Windows checks both passed on that SHA.
- PR #280 documentation handoff merged at `6f3e809b81fd3eb459213ab377e266884e4100d6`. Post-merge Python and Windows checks for that SHA were started; verify their final conclusions.
- Current branch `feat/top-of-book-spread-evidence` starts from main SHA `6f3e809b81fd3eb459213ab377e266884e4100d6`.

### Top-of-book spread collection — implementation in progress
- Added `PC_ENGINE/tools/run_top_of_book_collector.py`, a separate optional public-market observation process using existing ticker adapters for Binance bookTicker, OKX tickers and Coinbase ticker. It filters invalid/crossed markets, writes normalized ticker observations to `websocket_ticker_events.jsonl`, rotates one bounded backup, reconnects with backoff, and marks observations PAPER-only with orders/execution authorization false.
- Venue economic report now optionally reads the configured `evidence_reports.top_of_book` path (default `websocket_ticker_events.jsonl`) and computes mean quoted spread in bps from valid bid/ask pairs, only when the local receive timestamp is fresh and the minimum sample count is met. It rejects malformed, future, stale, crossed, non-PAPER-flagged or duplicate records and reports integrity counters.
- Defaults: 30-second freshness window, 20 valid observations required, and a bounded read of at most 100,000 records. Until the optional collector is run and enough valid data accumulates, spread remains unavailable/insufficient; do not infer it from trade prints.
- Dashboard now displays the measured spread and sample count only when the report marks spread evidence `AVAILABLE`; otherwise it displays the explicit unavailable/insufficient status.
- Added tests for Binance/OKX/Coinbase bid-ask parsing and spread report validity. Exact-head CI still needs to validate the branch.

### Safety and next actions
1. Inspect final diff and wait for exact-head Python tests plus Windows EXE build/smoke checks. Fix failures before merge.
2. Verify post-merge Python and Windows checks on the resulting main SHA.
3. The top-of-book collector is a separate opt-in process and is not automatically started by the trading runtime. No orders, credentials, private APIs, or REAL execution are involved.
4. Keep operational venue health, economic evidence and execution authorization independent. No cloud provisioning, deployments, paid services or spend without explicit authorization.

## 28. Handoff — 2026-09-30, public top-of-book spread collection merged

### Verified state
- PR #281 (`feat: collect public top-of-book spread evidence`) merged via squash at main SHA `05d8896ce29049a2d2f2e72d46557de8660f648a`.
- Exact-head checks on PR SHA `7a846e954ac54b0a78d10066b727acfc152c14b6` passed: Python tests run `36754312523` and Windows EXE build/smoke run `36754312460`.
- Post-merge Python run `36754653576` and Windows EXE run `36754653589` were still in progress at handoff creation. Do not call this main SHA fully validated until both finish successfully.

### Delivered in PR #281
- Added optional standalone public top-of-book collector `PC_ENGINE/tools/run_top_of_book_collector.py` using the existing public ticker adapters. It is not auto-started by the trading runtime. It writes normalized observations to `websocket_ticker_events.jsonl`, rotates one bounded backup, and retries failed connections with backoff.
- Fixed Binance `bookTicker` parsing for payloads without `e` event-type or `E` timestamp fields; added parser tests for Binance, OKX and Coinbase bid/ask observations.
- Venue economic evidence now optionally reads `evidence_reports.top_of_book` (default file `websocket_ticker_events.jsonl`) and calculates mean quoted spread in bps only from positive, non-crossed, fresh, deduplicated observations marked `paper_only=true`, `orders_submitted=false`, `execution_authorized=false`. Default max age 30 seconds, 20 observations minimum and 100,000-row bounded read.
- Added integrity counters and tests for malformed JSON, invalid/crossed quotes, non-PAPER rows, insufficient samples and end-to-end refresh integration. Dashboard shows measured spread and sample count only when evidence is available.
- The metric is quoted spread, not a complete executable trading cost estimate. It does not include a guaranteed fill, depth/market impact, fees, slippage or latency; these remain separate fields and require their own evidence.

### Safety and next steps
1. Verify post-merge Python and Windows EXE checks for SHA `05d8896ce29049a2d2f2e72d46557de8660f648a`.
2. If checks pass, next evaluate freshness/coverage diagnostics by venue and symbol, and ensure spread data is joined to the correct venue-symbol configuration without mixing symbols or stale data.
3. Keep the collector opt-in, bounded, public-data-only and separate from trading execution. No orders, credentials, REAL-mode changes, cloud provisioning, deployments, paid services or spend without explicit authorization.
4. Maintain separation between operational health, economic evidence, OOS uncertainty and execution authorization. Positive spread/OOS evidence is never permission to trade.


## 29. Handoff — 2026-09-30, top-of-book freshness/coverage diagnostics in progress

### Baseline
- PR #282 documentation handoff merged via squash at main SHA `35c0259fb56e499c7f5f5f376fa4cf6fe2d9abe0` after exact-head Python run `36754843073` completed successfully; PR was clean/mergeable.
- The public top-of-book collector from PR #281 remains optional, public-data-only and PAPER-only. It is not auto-started by the trading runtime.

### Current feature branch
- Branch: `feat/top-of-book-coverage-diagnostics`.
- Adds per-venue/per-symbol top-of-book coverage to the economic evidence report: valid observation count, last observation age, p50/p95 age and venue aggregate freshness.
- Stale observations remain excluded from spread evidence and coverage. Venue/symbol identities are kept separate; no aliases or symbols are mixed.
- Dashboard economics panel now surfaces symbol-level coverage and freshness alongside the existing spread metric, while keeping operational health and economic evidence separate.
- Added tests for venue-symbol coverage and freshness filtering. Exact-head CI still needs to validate the branch.

### Safety
- PAPER only; no order submission, REAL promotion, gate bypass, cloud provisioning, deployment, paid service or credential changes.

### Next actions
1. Validate exact PR-head Python tests and Windows EXE build/smoke.
2. Review the final diff and merge only if checks are green and PR is clean/mergeable.
3. Verify post-merge Python and Windows CI on the resulting main SHA.
4. Continue toward a genuinely installable PAPER-first Windows workflow; keep cloud activation and REAL execution explicitly gated.

## 30. Handoff — 2026-09-30, top-of-book operational heartbeat in progress

### Feature branch
- Branch: `feat/top-of-book-operational-heartbeat`, based on main SHA `23a06a492c2556835dfb9df8f0b4b94aeb30e0f0` after PR #283 was merged.
- Added operational state snapshots to `PublicWebSocketCollector`: connection attempts, message/event counts, last-event age, last error/close information and per venue-symbol state.
- The standalone top-of-book collector now writes an atomic `top_of_book_health.json` heartbeat alongside the bounded ticker evidence file. The heartbeat is refreshed every 5 seconds by default and records reconnect/collector/write counters.
- Health payloads remain explicitly PAPER-only with `orders_submitted=false` and `execution_authorized=false`.
- Added tests for collector operational snapshots and atomic heartbeat output.

### Safety / scope
- This is operational telemetry only. It does not auto-start the collector, submit orders, alter REAL gates, bypass readiness, create cloud resources, deploy or add paid services.
- The top-of-book collector remains a separate opt-in process; the trading runtime does not silently start it.

### Next actions
1. Validate exact-head Python and Windows EXE CI for this branch/PR.
2. Merge only after clean/mergeable PR and green required checks, then verify resulting main CI.
3. Use the new heartbeat as the source for a later dashboard feed-status layer: per exchange/platform, per symbol, connection state, last observation age, reconnects and data-write health.
4. Continue Windows PAPER resilience: clean installation, restart/recovery verification, bounded persistence and multi-day evidence accumulation. Keep operational health, economic evidence, OOS uncertainty and execution authorization separate.


## Current handoff — 2026-09-30, concrete browser PAPER surface

- PR #286 merged successfully at squash SHA `4fb21947f930021142c0b513f30097e3a6993080`.
- Exact-head CI for #286: Python tests run `36765400881` SUCCESS; Windows EXE run `36765400816` SUCCESS.
- Current implementation branch: `feat/browser-paper-adapter`.
- Existing repository browser execution work was preserved: `BrowserExecutionAdapter`, observed-target freshness safety and durable browser ledger remain separate and gated.
- Added `PC_ENGINE/execution/playwright_paper_surface.py` as the first concrete implementation of the transport-neutral surface contract.
- The new adapter supports headed/headless Chromium, optional persistent local profile, probe/observe feedback and deterministic PAPER BUY/SELL/CANCEL intent recording.
- The new adapter never clicks order controls, submits forms, calls private APIs or reports a simulated PAPER intent as an exchange fill.
- Added `tests/test_playwright_paper_surface.py` and `docs/EXECUTION_BROWSER_ADAPTER.md`.
- Next action: exact-head Python/Windows CI, inspect diff, then merge only if clean/green. After integration, add venue-specific browser observation/feedback safely; keep real submission behind existing execution/risk/readiness/RealModeGuard gates. Then implement Desktop and Android bridges separately.


## Current handoff — 2026-09-30, execution surface dashboard signalling

- PR #287 merged to main at `020e6ca15c8025ea405a98da5520876cb91e46ab` after exact-head Python SUCCESS (`36770762998`) and Windows SUCCESS (`36770762627`).
- Post-merge main CI is running for the merged SHA; do not infer completion until exact SHA results are checked.
- Current branch: `feat/execution-surface-dashboard`.
- Added read-only `/execution-surfaces` catalogue backed by `PC_ENGINE/diagnostics/execution_surface_catalog.py`.
- Dashboard now has a dedicated `Superfícies de execução` panel showing WEB_BROWSER, DESKTOP_APP, ANDROID_APK and HUMAN surface metadata when configured.
- The catalogue is deliberately configuration-only: `live_probe=false`; it cannot submit orders, probe private accounts or authorize REAL.
- Added tests and `docs/EXECUTION_SURFACE_DASHBOARD.md`.
- Next action: wait for post-merge main CI on `020e6ca...`, then validate exact-head CI for this branch. If green, merge. The following branch should connect persistent `ExecutionSurfaceStatus`/adapter feedback to the dashboard, exposing connection state, last feedback age, reconnects and data-write health while keeping operational health separate from economic evidence, OOS uncertainty and execution authorization.


## Current handoff — 2026-09-30, persistent execution surface feedback

- PR branch: feat/persistent-execution-surface-status.
- Base main was 6c78910956b90f73b5a8fc16d427bdf1b47010cf; post-merge Python and Windows checks on that main SHA both completed SUCCESS.
- Added PC_ENGINE/execution/surface_feedback_store.py: bounded local JSONL feedback persistence with atomic writes, retention cap, latest per venue/surface, feedback age, operational state, reconnect transitions and write-health telemetry.
- Extended PlaywrightPaperConfig with optional feedback persistence and connected browser adapter feedback to the store.
- Extended execution_surface_catalog to merge persistent transport telemetry into the existing read-only dashboard catalogue without inventing configured venues.
- Dashboard now shows connection state, last feedback age, reconnects, persistence/write health and source.
- Added unit tests for bounded persistence, stale classification, reconnect counting and browser feedback persistence.
- Added docs/PERSISTENT_EXECUTION_SURFACE_STATUS.md.
- Safety remains unchanged: all feedback is PAPER-only; no orders are submitted; execution authorization remains false; operational health is not economic/OOS/Risk/REAL evidence.
- Exact-head CI must validate this branch before merge. After merge, verify main CI on the resulting SHA.
- Next engineering sequence after merge: Desktop local bridge, then Android ADB/emulator/device bridge, both reusing the same transport feedback contract/store; continue Windows PAPER restart/recovery and bounded multi-day evidence.


## Handoff — 2026-09-30, Windows-first desktop PAPER local bridge

- PR #289 merged by squash at main SHA `145dd17f498a09853ba1dbacd5cbe41ffcf9a787`. Exact-head Python and Windows checks on #289 passed before merge.
- PR #290 is the active desktop bridge branch `feat/desktop-paper-local-bridge`, based on that main SHA; current head will be recorded after the final documentation commit.
- Added `PC_ENGINE/execution/desktop_paper_surface.py`: Windows-first local desktop surface adapter using a configured executable, local subprocess launch, process observation and optional read-only Windows UI Automation window-title inspection through optional `pywinauto`.
- Desktop CONNECT only launches the explicitly configured local application. OBSERVE/PROBE return deterministic operational feedback. BUY/SELL/CANCEL are PAPER intent records only: no order controls are clicked, no forms submitted, no private APIs called and no exchange fill is claimed.
- Reuses `ExecutionSurfaceFeedbackStore` for bounded local persistence and dashboard telemetry; all records remain PAPER-only and execution authorization remains false.
- Added `tests/test_desktop_paper_surface.py` and `docs/EXECUTION_DESKTOP_ADAPTER.md`.
- Next: validate exact-head Python and Windows EXE checks for PR #290; merge only when clean/mergeable and all required checks pass. Then verify post-merge main CI. Android ADB/emulator/device bridge follows, reusing the same surface contract and feedback store.


## Review update — 2026-09-30, desktop PAPER bridge hardening

Live GitHub verification at review time:
- Main remains at `145dd17f498a09853ba1dbacd5cbe41ffcf9a787` (PR #289 squash merge).
- PR #290 is open on `feat/desktop-paper-local-bridge`; the initially reviewed head was `0027640692ec50b990e79a2d3cd907f8eb1686be`, clean/mergeable, with Python test and Windows EXE checks successful on that exact SHA.
- Code review found cases not covered by the first green CI: process creation could be reported as connected even if the process exited immediately; an existing directory could be accepted as an executable path; OBSERVE feedback persistence used a generic probe request ID rather than the caller's request ID; process-name matching could be ambiguous.
- Hardened `PC_ENGINE/execution/desktop_paper_surface.py`: executable path must be a file; fast process exits are reported DOWN with the exit code; OBSERVE preserves the request ID in persisted feedback; Windows process-name observation uses CSV image-name exact matching and POSIX uses `pgrep -x`.
- Added regression tests for fast process exit, request-ID correlation in persisted feedback, and directory-as-executable rejection.
- Updated `docs/EXECUTION_DESKTOP_ADAPTER.md` to clarify process-liveness semantics and limits. These observations remain operational-only and do not prove exchange authentication, economic performance or permission to trade.
- The hardening commits were pushed to this same PR branch: adapter fixes `68e759a3425b62b9247a436b1bafa6123aa1448d` and `00fa540e46e2d58fe390b1c32ff474b02a05cfa0`, regression tests `05d9071f646e5d924ae10b26b1dda6db36b1e407`, adapter docs `3dd4b7c0fc368625954bce8ff72cc40d39f18752`, and context update `8dcda5f15835f84db657b823138861247cd8cab2`. A final request-ID correction was made in `00fa540...`; all CI must be checked against the resulting live PR HEAD after this context update. Do not merge based on any earlier SHA's green checks.
- Android bridge remains the next feature only after #290 has passed exact-head CI, been reviewed, merged, and the resulting main SHA has successful post-merge Python and Windows checks.
- PAPER-only safety unchanged: no order controls clicked, no forms submitted, no private exchange APIs called, no REAL authorization, no cloud resources or paid services.



## Desktop bridge final review — 2026-10-01

- Repository context was read from `main` at SHA `145dd17f498a09853ba1dbacd5cbe41ffcf9a787` before continuing.
- PR #290 remains the dedicated branch `feat/desktop-paper-local-bridge`, targeting `main`; do not infer its current HEAD from this note—query GitHub immediately before merge.
- The exact prior reviewed HEAD `c48d0b35d42bd59b2587210bd37ca4db1babe324` passed Python tests (PR run `36778539991`), Windows EXE (PR run `36778539998`) and Python push CI (`36778532171`). These checks do not cover subsequent changes below.
- Additional review hardening: commit `ff80161c5719a995a62c39f3b26cf139e29c9995` prevents repeated CONNECT from launching another child while the adapter's child is alive and removes raw UI window titles from persisted feedback; only a boolean title-filter match is retained.
- Regression tests were added in commit `93fedf247d577b9c2587a7cd5afd697dba870972` for duplicate CONNECT and window-title redaction. Adapter semantics were documented in commit `845b9b8b7b6ba29b2bbc1c37c743e527200ac559`.
- Final review requirements remain: inspect the complete diff; wait for both Python and Windows EXE checks to pass on the exact final PR HEAD; confirm the PR is open, mergeable and conflict-free; squash merge with expected HEAD SHA; then verify Python and Windows checks on the resulting `main` SHA.
- No merge has been performed at this checkpoint. Android bridge remains deferred until the Desktop PR and post-merge CI are complete.
- Safety: PAPER-only; no order UI interactions, private APIs, REAL authorization, cloud resources, paid services, or automatic runtime startup. Window titles are not stored verbatim; process-liveness evidence is operational only.


## Handoff — 2026-10-01, Android ADB PAPER bridge in progress

### Verified baseline (supersedes earlier desktop handoff status above)
- PR #290 (Windows-first desktop PAPER local bridge) was squash-merged to `main` at `24c28f86af3af8880792524f1fd3849ea307c945`.
- Post-merge Python tests passed: run `36811401254`, https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/36811401254 .
- Post-merge Windows EXE build/smoke passed: run `36811401232`, https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/36811401232 .
- Android work is isolated on `feat/android-adb-paper-bridge`, based on that verified main SHA.

### Android implementation
- Added `PC_ENGINE/execution/android_adb_paper_surface.py` with `AndroidAdbConfig` and `AndroidAdbPaperSurfaceAdapter`, reusing the existing transport-neutral contract and bounded feedback store.
- Read-only ADB operations: resolve adb, run `adb version`, enumerate `adb devices -l`, optionally inspect a configured package process with `adb shell pidof`.
- Explicit states include `ADB_UNAVAILABLE`, `NO_DEVICE`, `DEVICE_UNAUTHORIZED`, `DEVICE_OFFLINE`, `MULTIPLE_DEVICES`, `APK_NOT_CONFIGURED`, `APP_NOT_OBSERVED`, `APP_OBSERVED`, and `COMMUNICATION_ERROR`.
- Configurable command timeout, optional device serial/package, persistent request-correlated feedback and bounded retention. Raw device serials and raw ADB output are not persisted in feedback details.
- `CONNECT` is observation-only; it does not install or launch an APK. BUY/SELL/CANCEL are PAPER intent records and never invoke ADB or interact with the Android UI.
- Added `tests/test_android_adb_paper_surface.py` and `docs/EXECUTION_ANDROID_ADB_ADAPTER.md`, covering missing ADB, empty device list, unauthorized/offline/permission states, malformed output, timeouts, multiple devices, package/app states, request correlation and no ADB invocation for PAPER intents.

### Validation gates and next steps
1. Review the exact current PR diff and run Python tests plus Windows EXE build/smoke on the final PR HEAD.
2. Fix all failures and re-run checks; merge only when the PR is open, clean/mergeable, and all required exact-head checks pass.
3. After merge, verify both Python and Windows checks on the resulting `main` SHA.
4. Do not provision SDK/ADB, install drivers/APKs, enable developer options, authorize devices, or perform any cloud/paid action automatically. These remain explicit local user actions.
5. Keep PAPER as default. No order submission, private API use, credential/OTP/session capture, MFA/CAPTCHA bypass, REAL-mode changes, risk/readiness gate bypass, or automatic trading-runtime startup.


## 31. Handoff — 2026-10-01, Android ADB PAPER bridge merged and verified

### Verified repository state
- Main SHA: `d412b52b75a4dee52985c37a2b41ff085059b48e`.
- PR #291 (read-only Android ADB PAPER bridge) was squash-merged: https://github.com/AndreVazao/VazaoSovereignTrader/pull/291
- Exact PR-head checks on `605fcd4c79d5da91ac90a7c509efe6b0dbd75e38` passed:
  - Python tests run `36814308848`: SUCCESS.
  - Windows EXE build/smoke run `36814313304`: SUCCESS.
- Post-merge checks on the exact resulting main SHA `d412b52b75a4dee52985c37a2b41ff085059b48e` passed:
  - Python tests run `36814698151`: SUCCESS.
  - Windows EXE build/smoke run `36814698203`: SUCCESS.
- No open PRs were present after the merge. No cloud resources or paid services were created.

### Current execution surface adapters
- Browser PAPER adapter, persistent feedback store/dashboard catalogue, Windows desktop PAPER bridge, and Android ADB PAPER bridge are present on main.
- Desktop and Android actions remain observational/PAPER-only. Android CONNECT does not install or launch APKs; BUY/SELL/CANCEL only record PAPER intent.
- Surface feedback is operational telemetry only and never grants execution authorization or proves exchange authentication, economic quality, or profitability.

### Next engineering focus
1. Audit the runtime integration of browser/desktop/Android adapters and their feedback paths. Confirm which adapters are instantiated by the app versus currently being library components, and do not add automatic device control or trading-runtime startup.
2. Harden feedback persistence health reporting: the dashboard constructs its own feedback-store instance, so process-local write-error counters may not reflect write failures from another adapter instance or prior process. Define and test a truthful durable/observable health contract before showing a green status.
3. Continue Windows PAPER restart/recovery verification and bounded multi-day evidence collection. Report missing/stale evidence explicitly; never infer readiness from file existence alone.
4. Keep all changes PAPER-only. Never submit orders, activate REAL, bypass readiness/preflight/reconciliation/Risk Engine/RealModeGuard, provision cloud resources, deploy, or incur costs without André's explicit authorization.
5. For each feature, use a dedicated branch and PR; inspect the exact final diff and exact-head CI, merge only when clean/mergeable and required checks are green, then verify Python and Windows EXE checks on the resulting main SHA.


## 32. Handoff — 2026-10-01, execution-surface runtime wiring audit

### Scope
- Baseline verified main SHA: `3892b9c23d9cd7152570f7561f1c2958fce0fcdc`.
- Post-merge Python tests run `36815891620`: SUCCESS.
- Post-merge Windows EXE build/smoke run `36815891648`: SUCCESS.
- The runtime audit does not start browsers, desktop applications, ADB devices, APKs, or trading runtimes.

### Truthful dashboard/runtime signal
- The execution-surface catalogue now exposes an explicit `adapter_runtime_audit` inventory for WEB_BROWSER, DESKTOP_APP, and ANDROID_APK.
- Each configured venue identifies its concrete PAPER adapter implementation.
- `runtime_wiring=FEEDBACK_SEEN` is emitted only when persisted runtime feedback exists for that venue/surface.
- `runtime_wiring=NOT_OBSERVED` and `library_only=true` make the absence of runtime feedback explicit; configuration alone is not presented as an active adapter.
- The audit is observational telemetry only and does not imply authentication, execution authorization, profitability, or readiness.

### Validation
- Added catalog tests covering both library-only/configuration state and persisted runtime-feedback evidence.
- PAPER-only guarantees remain unchanged: no order UI interaction, no private API calls, no APK installation/launch, no order submission, and no REAL-mode changes.


## 33. Handoff — 2026-10-01, explicit execution-surface adapter registry

- Baseline main SHA: `f2205920763d98f3635db53f1672e5b92e160312`, after PR #294 and its post-merge Python/Windows verification.
- Added `PC_ENGINE/execution/surface_adapter_registry.py` as the single explicit registration point for the PAPER browser, desktop and Android adapters.
- The dashboard/catalog audit now distinguishes:
  - `adapter_registered=true`: a concrete adapter implementation is registered for the surface.
  - `adapter_instantiated=false`: the catalogue itself has not instantiated or started a transport.
  - `runtime_wiring=FEEDBACK_SEEN`: persisted runtime feedback exists, but this remains evidence of observed transport telemetry rather than proof of a specific adapter instance.
  - `runtime_wiring=NOT_OBSERVED`: no persisted runtime feedback was observed.
- The registry exposes a controlled `instantiate_adapter()` path for future runtime wiring. Instantiation alone does not probe, launch, connect or submit an order.
- Tests verify all supported surfaces are registered and that constructing the adapters does not create feedback files or start a transport.
- This change is observational/structural only. It does not alter execution authorization, readiness, Risk Engine, reconciliation or RealModeGuard.
- PAPER-only guarantees remain unchanged: no exchange order submission, no private API trading, no credential persistence, no automatic browser/desktop/ADB startup.


## 34. Handoff — 2026-10-01, explicit execution-surface runtime lifecycle

- Baseline main SHA: `4c35528c6f6358bea13db2a3f7fdc039df746556`; post-merge Python and Windows verification for PR #295 both passed on this exact SHA.
- New branch: `feat/explicit-surface-runtime-lifecycle`.
- Added `PC_ENGINE/execution/surface_runtime.py` with an explicit PAPER-only lifecycle manager.
- Lifecycle states distinguish REGISTERED, INSTANTIATED, PROBED, CLOSED and PROBE_FAILED.
- Instantiation delegates to the explicit adapter registry but does not call probe/observe/execute and therefore does not start a browser, desktop process or ADB operation.
- Probing is a separate explicit call. The runtime snapshot records actual in-process instances and feedback state without treating them as execution authorization.
- Added `tests/test_surface_runtime.py` covering inert instantiation, explicit probing and close lifecycle.
- Added `docs/EXECUTION_SURFACE_RUNTIME.md`.
- Safety remains PAPER-only: no order submission, no private trading API, no automatic runtime startup, no credential persistence and no changes to readiness/Risk Engine/reconciliation/RealModeGuard.


## 35. Handoff — 2026-10-01, explicit application runtime lifecycle integration

- Baseline main SHA: `57ccca2c870cb8d628052cf8343286b3c11e3d6a`; post-merge Python and Windows checks both passed on that exact SHA before this feature started.
- Added `PC_ENGINE/execution/surface_runtime_manager.py` as the application-owned bridge between configuration and the explicit PAPER lifecycle manager.
- The manager is instantiated when the Flask application is created, but it contains no adapters until an explicit lifecycle request is made.
- Added explicit API lifecycle endpoints:
  - `GET /execution-surfaces/runtime`: reports actual in-process lifecycle records.
  - `POST /execution-surfaces/runtime/instantiate`: explicitly creates one configured PAPER adapter instance.
  - `POST /execution-surfaces/runtime/probe`: explicitly performs transport observation for one instantiated runtime.
  - `POST /execution-surfaces/runtime/close`: explicitly closes one runtime.
- Lifecycle control endpoints require the existing `trade_paper` scope; the read-only snapshots remain under `read_private_state`.
- Existing `browser.platforms` remains supported. A new optional `execution_surface.platforms` map can configure WEB_BROWSER, DESKTOP_APP and ANDROID_APK with shared feedback persistence defaults.
- The dashboard catalogue now accepts the actual runtime snapshot and reports `adapter_instantiated`, `runtime_id`, `runtime_state` and `IN_PROCESS_*` wiring only when a real in-process lifecycle record exists. CLOSED records are not presented as active instances.
- No automatic browser launch, desktop process launch or ADB invocation was introduced. Probe remains the first explicit operation allowed to touch a transport.
- All lifecycle APIs remain PAPER-only: no order submission, private trading API, credential persistence, readiness/Risk Engine/reconciliation/RealModeGuard bypass, cloud resource or paid-service creation.
- Added tests for inert manager construction, explicit browser instantiation without probing, desktop/Android config construction, fail-closed missing configuration and truthful catalogue runtime overlay.
- Added `docs/EXECUTION_SURFACE_RUNTIME_INTEGRATION.md`.


## 36. Handoff — 2026-10-01, runtime lifecycle identity hardening

- Baseline main SHA: `0409e019be3f28fda7c132631ff17187f96f1964`; Python and Windows post-merge checks for the previous integration were green before this feature.
- Hardened `ExecutionSurfaceRuntime` so a `runtime_id` is process-lifetime unique: a CLOSED runtime cannot silently reuse the same identity and overwrite historical lifecycle state.
- Added an adapter surface-binding check immediately after registry instantiation; any adapter reporting a surface different from the requested surface fails closed before the runtime is recorded active.
- Hardened `ExecutionSurfaceRuntimeManager.build_adapter_config()` to reject a configured venue when its declared `surface` conflicts with the requested surface. This prevents accidentally constructing a desktop/Android adapter from a browser-configured venue (or vice versa).
- Added regression tests for runtime-ID reuse, adapter surface mismatch and configured surface mismatch.
- No transport is started by these checks; all changes remain PAPER-only and observational. No order path, credentials, readiness, Risk Engine, reconciliation or `RealModeGuard` behavior was changed.


## 37. Handoff — 2026-10-01, explicit runtime health/staleness
- Added observational runtime health to \`PC_ENGINE/execution/surface_runtime.py\`.
- Health is derived only from explicit probe feedback timestamps: \`NEVER_PROBED\`, \`FRESH\`, \`STALE\`, \`PROBE_FAILED\`, \`CLOSED\`.
- Snapshot now reports \`feedback_age_ms\`, \`stale\`, \`last_feedback_at_ms\`, and an explicit health policy. Default stale threshold is 30 seconds and can be configured with \`execution_surface.runtime_health_stale_after_ms\`.
- \`ExecutionSurfaceRuntimeManager\` owns the configuration bridge; negative thresholds fail closed.
- \`execution_surface_catalog.py\` exposes runtime health/staleness without inferring health from configuration or adapter registration.
- No background heartbeat, automatic probe, reconnect, restart, or execution authorization was introduced.
- Recovery remains explicit and runtime IDs remain process-lifetime unique.
- Health is deliberately separate from authentication, market-data quality, strategy readiness, reconciliation, Risk Engine, and \`RealModeGuard\`.
- Tests cover never-probed, fresh, stale, probe-failed, closed, configuration, and catalog semantics.


## 38. Handoff — 2026-10-01, instalação pronta para recolha pública de market data
- Adicionado public market-data bootstrap em PC_ENGINE/radar/public_market_data_bootstrap.py.
- O bootstrap verifica ticker + OHLCV público por venue/símbolo e aplica o Data Quality Gate antes de produzir market_data_bootstrap.json.
- Adicionado CLI PC_ENGINE/tools/run_market_data_bootstrap.py e script Windows scripts/verify_public_market_data.ps1.
- O bootstrap é explicitamente público/read-only: não usa credenciais privadas, balances, autenticação ou ordens.
- A configuração de exemplo passa a observar BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT e DOGE/USDT nos WebSockets públicos Binance/Coinbase/OKX.
- verify_pc_install.ps1 verifica também a presença do bootstrap e do collector contínuo.
- O collector WebSocket existente continua separado do PC Engine e grava health + eventos + aprendizagem PAPER.
- A instalação operacional passa a ter sequência clara: setup -> verify install -> verify public market data -> install Windows autostart.
- Nada nesta fase ativa REAL ou altera os gates de Risk Engine, reconciliation, readiness ou RealModeGuard.


## 39. Handoff — 2026-10-01, one-click Windows installer + operator file exchange

This feature adds a distributable Windows installation path intended to replace the multi-step first-install PowerShell sequence for normal users.

### Windows installer

- `installer/VazaoSovereignTrader.iss` defines an Inno Setup installer.
- `scripts/build_windows_installer.ps1` builds two frozen executables:
  - `VazaoSovereignTrader.exe` — PC engine, with Playwright Chromium bundled for the browser execution surface.
  - `VazaoSovereignTrader-MarketData.exe` — continuous public/read-only market-data collector.
- `.github/workflows/windows-installer.yml` builds the installer in GitHub Actions and uploads a single `.exe` artifact.
- The installer is user-local under `%LOCALAPPDATA%\\VazaoSovereignTrader` and does not require administrator elevation.
- The installer creates Windows logon tasks for the engine and market-data collector and starts the engine after installation.
- Configuration is preserved on upgrades; `config.local.json` is only created from the example when it does not already exist.
- Runtime remains PAPER/read-only; installation never creates exchange credentials, submits orders or enables REAL execution.

### Operator file exchange

Two explicit folders are created below the installed runtime:

- `data/operator_exchange/INBOX`: operator/mobile -> PC.
- `data/operator_exchange/OUTBOX`: PC -> operator/mobile.

The authenticated API exposes only these folders through:

- `GET /operator-files`
- `POST /operator-files/upload` (INBOX only, bounded upload size)
- `GET /operator-files/<folder>/<filename>`

Path traversal is rejected and arbitrary filesystem paths are never exposed. The mobile cockpit now has file exchange controls; Android uses the system document picker for upload/download targets. The downloaded OUTBOX file can therefore be saved to a user-selected phone location and then attached/shared from the phone.

### Scope

This is deployment/operator infrastructure only. It does not change the execution authorization chain. The architecture remains PAPER-first and preserves readiness, reconciliation, Risk Engine and `RealModeGuard` boundaries.


## 40. Handoff — 2026-10-01, Windows installer bundle-size hardening

The first merged installer pipeline produced a Windows Actions artifact too large for the connected artifact handoff limit. The installer is being adjusted so Playwright Chromium is bundled once as a separate `ms-playwright` directory instead of being embedded inside the frozen engine executable.

- Build installs Chromium to `installer/build/ms-playwright`.
- The Inno Setup package installs that browser bundle under the application directory.
- Frozen `PC_ENGINE/main.py` sets `PLAYWRIGHT_BROWSERS_PATH` to the installed bundle path before importing the engine.
- The goal is a normal downloadable setup artifact while retaining offline-first installation and avoiding a separate browser download on the operator's PC.
- This remains PAPER/read-only and does not change execution authorization.
- The exact-head Windows installer artifact must pass build and smoke tests, and its size must be checked before the package is considered ready for handoff.


## 41. Handoff — 2026-10-01, Android first-pairing and reconnect foundation

- Baseline main SHA: `e4c7b1398a228b72e5a0fea21efccfc465fb77f4`; post-merge Python tests and Windows EXE (including installer job) are green on that exact SHA (runs 36839565488 and 36839565481).
- Branch: `feat/android-first-pairing-reconnect`.
- Android cockpit now loads and saves the PC endpoint in its private app data after a successful connection; only the endpoint is persisted, never the local API token.
- Existing polling provides retry attempts while the app is running, with explicit offline/reconnect status text.
- Added `scripts/pair_android_usb.ps1`: requires exactly one authorized Android device, supports optional APK install, and creates a temporary ADB reverse tunnel for port 8765. It never reads/prints tokens and does not bypass Android user authorization.
- Added `docs/ANDROID_FIRST_PAIRING.md` and updated the mobile README to explain USB bootstrap, LAN setup, Tailscale remote access, endpoint persistence and current limitations.
- Important limitations remain explicit: no cryptographic one-time pairing challenge/device revocation yet; no Android Keystore-backed token persistence; the operator must enter the token again after a fresh app process; Tailscale installation/sign-in remains user-driven; USB reverse is temporary only.
- No direct Internet port forwarding, cloud provisioning, private exchange API, order submission or REAL-mode changes.
- Next work after CI/review: implement PC-approved one-time pairing and revocable device identity with Android Keystore-backed secret storage, then a guided LAN/Tailscale connection diagnostic.


## 42. Handoff — 2026-10-01, Android APK dependency compatibility repair

- Android CI on PR #304 exposed a build failure in python-for-android's pure-Python dependency installation: it resolved a CPython 3.14 Android wheel for `charset-normalizer`, then pip rejected that wheel in the build environment. The failure was confirmed from the exact workflow job logs.
- Removed the explicit `requests` and `charset-normalizer` app requirements and migrated the mobile cockpit's HTTP calls to Python's standard-library `urllib`, including JSON requests/responses and multipart file upload. This avoids the problematic requests dependency resolver path and keeps Android networking dependency-light.
- The change is on `feat/android-first-pairing-reconnect`; do not merge until the Android APK workflow, Python tests and Windows EXE/installer workflow pass on the exact same PR head.
- This is a transport implementation change only: API token remains in memory and is not persisted; only the successful PC endpoint is saved in app-private storage. No trading execution, exchange credentials, public port forwarding or REAL-mode changes.


## 43. Handoff — 2026-10-01, Android USB bridge merged and post-merge CI verified

- Verified live GitHub main HEAD: `2b9351de72e21f3920e4b01000b704514c4412f5`.
- PR #304, `feat(android): add USB first-pairing and reconnect foundation`, merged by squash into main at the above SHA. PR: https://github.com/AndreVazao/VazaoSovereignTrader/pull/304
- Exact PR-head SHA before merge: `d61124fb97cf05e2c0b208e5bbb78715220d5149`. Python tests, Windows EXE, and Android APK workflows completed successfully on this SHA. The Windows workflow also completed the installer job successfully.
- Post-merge CI is now verified green on exact main SHA `2b9351de72e21f3920e4b01000b704514c4412f5`: Python tests, Windows EXE, and installer all completed with success. Runs: https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/36895961808 and https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/36895961777
- Android mobile cockpit persists only the PC endpoint in app-private storage after a successful connection; the control token is not persisted and must be entered again after a fresh app process. HTTP transport uses Python standard-library urllib to avoid the python-for-android dependency resolution failure.
- `scripts/pair_android_usb.ps1` requires exactly one authorized ADB device, optionally installs a configured APK, and establishes a temporary `adb reverse` tunnel for local bridge port 8765. USB debugging is still user-authorized; no credentials are read or printed.
- Explicitly unimplemented: cryptographic one-time pairing challenge, revocable per-device identity, Android Keystore token storage, and guided LAN/Tailscale diagnostics. The current USB tunnel is temporary and does not itself provide a complete pairing protocol.
- Safety unchanged: PAPER is default; no order submission, no exchange credentials, no public port forwarding, no cloud provisioning, and no REAL-mode gate changes.
- Next engineering step: create one dedicated feature branch/PR for PC-approved one-time pairing, revocable device identity, Android Keystore-backed secret storage, and tests for replay, expiry, unauthorized device, revocation, reconnect, and malformed requests. Keep all secrets out of source/logs. Do not claim hardware validation until tested against a real authorized Android device and Windows PC.
- The main context file previously lagged behind the live repository; this handoff must be merged through a dedicated documentation PR rather than direct edits to main.


## 44. Secure Android device pairing — implementation branch opened 2026-10-01

Current implementation branch: `feat/android-revocable-device-pairing`, based on main SHA `1f882c28ba2cb104d936d425f91a2c3dc9ec5b9a`. Do not treat this work as merged or hardware-validated until its PR, exact-head CI, review, merge, and post-merge CI are complete.

Files added/changed in this branch:
- `PC_ENGINE/core/mobile_pairing.py`: local JSON registry; five-minute one-time challenge; explicit approval state; SHA-256 token hashes; random per-device bearer tokens; atomic writes and cross-process locking; active/revoked state; restricted scopes `read_private_state`, `trade_paper`, and `respond_human_interaction`; throttled last-seen persistence.
- `PC_ENGINE/api/server.py`: owner-token-protected challenge creation/status/completion, device listing, and server-side revocation routes. Device tokens authenticate as separate principals; malformed pairing-store state fails device auth closed while retaining owner-token recovery.
- `MOBILE_APP/secure_token.py`: Android Keystore AES-GCM encryption/decryption of the device token; fails closed off Android and never writes plaintext.
- `MOBILE_APP/main.py`: pairing UI, temporary owner-token use, approval status check, Keystore persistence, local token forgetting, and UI-level block on REAL actions for paired device tokens.
- `scripts/approve_mobile_pairing.py`: explicit local-console approval requiring selected device, code from Android, and typed `APROVAR`.
- `scripts/revoke_mobile_device.py`: explicit local-console revocation requiring selected device and typed `REVOGAR`.
- Tests: `tests/test_mobile_pairing.py`, `tests/test_mobile_pairing_api.py`, `tests/test_mobile_secure_token.py`.
- `docs/ANDROID_FIRST_PAIRING.md`: setup, pairing, revocation, limitations, and hardware-validation status.

Security invariants:
- Pairing challenges expire after five minutes and cannot be completed twice.
- The raw device token and confirmation code are not persisted; only the device-token SHA-256 digest is stored.
- Device tokens have only `read_private_state`, `trade_paper`, and `respond_human_interaction` scopes. The last scope permits responding to an explicit PC-originated human prompt only; it does not grant prompt creation, owner settings, `trade_real`, or exchange-account management. Source-mode registry path is `PC_ENGINE/data/mobile_pairing`; the packaged EXE defaults to `data/mobile_pairing` beside the EXE.
- PC console approval is separate from mobile challenge creation and requires the six-digit code shown on the phone.
- Android token persistence uses a non-exportable AES-GCM key in Android Keystore; storage failure triggers a server revocation attempt and no plaintext fallback.
- The existing owner token is never saved in mobile config. It is required temporarily to initiate and complete pairing.
- `ESQUECER` removes local material only; server-side revocation is separate and is provided by the PC console helper.
- No public port forwarding, cloud provisioning, exchange credential handling, order submission, or REAL-mode gate modification.

Review points before merge:
- Confirm Android python-for-android packaging can import `secure_token.py` and that Pyjnius Java-array / AndroidKeyStore calls work on a real supported device.
- Check route authorization and response semantics, malformed/corrupt registry handling (including owner-token recovery), cross-process writes, challenge expiry, replay, revocation, and scope restriction.
- CI must run Python tests, Windows EXE, installer, and Android APK on the exact PR head SHA. These checks and physical Android validation are not yet claimed as complete.
- Keep PAPER as default and do not claim end-to-end pairing validated until an authorized physical Android device and Windows PC have completed the flow.


## 45. Handoff — 2026-10-01, secure Android pairing review continuation

- PR #306 remains open: https://github.com/AndreVazao/VazaoSovereignTrader/pull/306
- Implementation branch: `feat/android-revocable-device-pairing`. Before this context-only update, latest implementation/docs fix SHA was `c118d1c65ee9a3e159a6cda0d3cdbe638466d0c8`; use live GitHub for the exact current head after this commit.
- Exact-head Python checks passed on `4fa07d244124af8ba1ae48556059d6da7686e7dc`. The docs correction that removes contradictory pre-pairing instructions triggered a new CI cycle; Python, Windows EXE/installer, and Android APK checks on the final head must be verified before merge.
- The Windows EXE build job succeeded on the previous head, but the installer subjob was still running. Android APK build was still running. Do not infer success from jobs on older SHAs.
- Review found and corrected stale wording in `docs/ANDROID_FIRST_PAIRING.md`: the owner token remains non-persistent, while the paired device token is encrypted with Android Keystore; no plaintext fallback exists.
- Added hardening tests for five-minute challenge expiry, corrupt registry fail-closed behaviour, and recovery of owner-token authentication when the pairing registry is corrupt. The latest Python suite passed on the implementation SHA before the docs-only fix.
- Remaining review: inspect exact final diff, confirm all required exact-head checks green, ensure PR mergeable, squash merge, then verify main SHA and post-merge CI. Physical Android/Windows pairing validation remains unperformed until a real authorized device completes the flow.
- No REAL-mode changes, cloud resources, public port forwarding, exchange credentials, or live orders are authorized or introduced.


## 46. Verified handoff — 2026-10-01 UTC

### PR #306 — secure revocable Android pairing
- Merged by squash after exact-head checks passed.
- PR head: `dffd04b925c58fca6c53b3239c9b48052eb93915`.
- Merge commit / current main at branch start: `82865d584d5d81daabfcee4a9f42dd73f4b77448`.
- Exact-head CI passed: Python tests (run 36918083737), Android APK (run 36918083729), Windows EXE/installer (run 36918083616).
- Post-merge Python and Windows workflows were queued at the time of verification; check their final status on merge SHA before declaring post-merge CI complete.
- Physical Windows + Android pairing / OEM Keystore validation remains unperformed.

### Current implementation branch — Android ADB bridge hardening
- Branch: `feat/android-adb-device-bridge`, created from main after PR #306 merge.
- Existing adapter: `PC_ENGINE/execution/android_adb_paper_surface.py`; runtime manager is explicitly inert until instantiate/probe calls.
- Changes in progress: reject mismatched surface actions instead of treating them as Android actions; give direct probe/observe calls unique correlation IDs; add regression tests and `docs/ANDROID_ADB_BRIDGE.md`.
- Android ADB operations remain read-only, bounded by subprocess timeouts, and use `shell=False`. No automatic install/launch, no UI interaction, no live orders, no REAL authorization.
- Exact branch head after initial code/test changes must be read live from GitHub. Wait for exact-head Python and Windows CI, inspect final diff, create PR, and merge only if checks pass and no blocking defect.
- After merging this bridge-hardening PR, verify all post-merge workflows and update this context with the actual SHA/results.


## 47. Verified handoff — 2026-10-02 UTC

### PR #307 — Android ADB PAPER bridge hardening
- PR: https://github.com/AndreVazao/VazaoSovereignTrader/pull/307 — merged by squash.
- Implementation head before merge: `08f893f9f4bdb42c2f9f3602b2328a3402d770dd`.
- Merge commit and current main at this handoff: `54caed8d584f09c75aca50a6b836425a7e525610`.
- Exact-head PR Python tests passed: run 36920600519. Exact-head Windows EXE and installer passed: run 36920600487.
- Post-merge Python tests passed on main SHA `54caed8d584f09c75aca50a6b836425a7e525610`: run 36921375392.
- Post-merge Windows EXE and installer passed on main SHA `54caed8d584f09c75aca50a6b836425a7e525610`: run 36921375538.
- Verified main SHA directly from GitHub. At verification time there were no open pull requests.
- Code changes: mismatched non-ANDROID_APK surface actions are rejected before ADB invocation; probe/observe request IDs are unique; regression tests and `docs/ANDROID_ADB_BRIDGE.md` added.
- Safety boundary unchanged: ADB bridge is read-only operational telemetry, no APK installation/launch, no UI automation/order submission, PAPER-only, no REAL authorization.
- PR #306 secure revocable Android pairing is also merged at predecessor main SHA `82865d584d5d81daabfcee4a9f42dd73f4b77448`; physical Android/Windows pairing and Android Keystore/OEM validation remain unperformed.

### Next actions
1. Continue from this exact main SHA and create a dedicated feature branch/PR for the next bounded implementation task.
2. Prefer reliability and testability work for continuous PAPER data collection/research; inspect the current code and tests before choosing the change.
3. Preserve fail-closed risk/readiness/RealModeGuard boundaries, no silent runtime start, no secrets, no cloud costs, and no REAL order submission.
4. Require exact-head CI and post-merge CI verification; physical device/emulator validation remains an explicit outstanding item.


## 48. Handoff — 2026-10-02 UTC: bounded PAPER market-data persistence

- PR #308 merged by squash; merge commit/current main at start of next implementation: `76b745cb9295f4168d6c9c3a2b60fff1c443fea7`.
- PR #308 exact-head Python CI passed: run 36961284224. PR #307 post-merge Python and Windows EXE/installer passed on predecessor main SHA `54caed8d584f09c75aca50a6b836425a7e525610` (runs 36921375392 and 36921375538).
- PR #309 (`feat/bounded-top-of-book-persistence`) merged by squash as `cabd98b20d49eeba924eb6f776bbd2ab775e7f4d`.
- Exact-head Python tests passed: run 36961681763. Windows EXE and installer build/smoke tests passed: run 36961681739, both on head `aaa9319ea1ecd9461aabe01320cb02097fde390e`.
- The collector now drops a serialized top-of-book record that exceeds the configured byte cap without modifying existing output, increments `oversized_tickers_ignored`, and keeps normal output/backup rotation bounded. Regression tests cover oversized drops and rotation caps.
- This is observational/PAPER-only; no exchange execution, order submission, risk controls, REAL authorization, or service auto-start changed.
- Post-merge CI on resulting main SHA `cabd98b20d49eeba924eb6f776bbd2ab775e7f4d` was queued at handoff; verify Python and Windows EXE/installer workflows to completion.
- Physical Android/Windows pairing and Android Keystore/OEM validation remain outstanding.


## 49. Verified handoff — 2026-10-02 (PR #311)

### Current main and CI
- PR #311: https://github.com/AndreVazao/VazaoSovereignTrader/pull/311
- Purpose: reject malformed top-of-book ticker values without allowing numeric conversion failures to escape validation.
- Merged commit / current main at handoff: `364ee150bcfe29e073d6ce8905099fdd6ccfe394`.
- Exact PR head: `ad33958798977562de7fc3114a7347e0bb272537`.
- Exact-head Python tests: run 36964990001 SUCCESS.
- Exact-head Windows EXE and installer: run 36964989999 SUCCESS.
- PR #310 post-merge Python run 36963300302 SUCCESS on main `b9d0a148c3496e4af577664e8b62b56405b3ca50`.
- PR #310 post-merge Windows EXE/installer run 36963300317 SUCCESS on main `b9d0a148c3496e4af577664e8b62b56405b3ca50`.
- Post-merge CI for PR #311 on `364ee150bcfe29e073d6ce8905099fdd6ccfe394` must be checked after this handoff; the PR-triggered exact-head CI above is green.

### Code change
- Added `_is_valid_top_of_book(event)` in `PC_ENGINE/tools/run_top_of_book_collector.py`.
- Rejects non-numeric bid/ask, NaN/infinity, non-positive bid, ask <= bid, malformed/missing fields and non-positive/invalid local receive timestamp.
- Regression tests cover malformed bid, non-finite values, invalid market values, invalid timestamp and valid numeric-string inputs.
- Invalid records are discarded before serialization; PAPER-only collection semantics remain unchanged.
- No order submission, REAL-mode authorization, secrets, cloud provisioning or auto-start changes.

### Platform execution capability — explicit gap, do not overstate
- `PC_ENGINE/execution/surface_adapters.py` defines shared surfaces and actions for WEB_BROWSER, DESKTOP_APP and ANDROID_APK, including BUY/SELL/CANCEL action kinds and shared feedback structures.
- `AndroidAdbPaperSurfaceAdapter` currently performs bounded, read-only ADB observation. CONNECT/OBSERVE only probe; BUY/SELL/CANCEL record PAPER intent and do not interact with app UI or submit orders.
- ADB docs explicitly state there is no APK installation/launch, UI interaction, private API call or order submission. Physical Android/emulator/OEM validation remains outstanding.
- Do not claim that browser/desktop/Android order execution is complete merely because surface abstractions or a dashboard exist. Inspect the live implementation and tests before each capability claim.

### Next actions
1. Verify post-merge Python and Windows EXE/installer workflows on commit `364ee150bcfe29e073d6ce8905099fdd6ccfe394`.
2. Continue one implementation PR at a time. First inspect current platform-runtime registry, authenticated endpoints, browser/desktop adapters, RealModeGuard/Risk Engine and order reconciliation code to establish actual supported paths.
3. Build a capability matrix per venue and surface: observe; authenticated state; order preview; PAPER submission/simulation; cancel/replace; fill/balance reconciliation; timeout/unknown-outcome recovery; supported REAL pathway. Mark unimplemented items honestly.
4. Implement one safe, testable platform capability per branch/PR. Keep Android auth/MFA/CAPTCHA and anti-bot boundaries intact; never store exchange credentials in code/logs.
5. REAL execution remains disabled unless the existing independent readiness, preflight, risk, RealModeGuard, operator authorization and reconciliation gates are all satisfied. Do not enable it as part of platform-interaction work.


## 50. Platform reconnaissance inventory — implementation PR in progress

### Latest verified main / browser execution semantics
- PR #313: https://github.com/AndreVazao/VazaoSovereignTrader/pull/313 — merged by squash as `fd34043a974d93f1549751e9668da3d9a808bb6a`.
- Exact PR head: `6e2a29db4c19c32bbb1240bc485c0e374ea65389`; Python run 37008766071 SUCCESS; Windows EXE/installer run 37008766213 SUCCESS.
- Post-merge Python run 37009849727 and Windows EXE run 37009849783 were still in progress at handoff; verify both against the resulting main SHA before closing this item.
- Browser terminal outcomes now preserve FILLED/PARTIAL/CANCELLED/REJECTED distinctions and retries do not blindly resubmit after a durable prior submission.

### New capability in branch `feat/platform-reconnaissance-inventory`
- Added `PlaywrightPaperSurfaceAdapter.inspect_current_page()`, an explicit, read-only inventory of visible page headings, buttons, navigation labels, form count and visible input-type counts.
- The inventory does not click controls, navigate automatically, read input values, cookies/storage, balances, positions or credentials. It reports only the page origin, bounds labels, and redacts common email/long-number patterns.
- The report explicitly marks account data as not read and execution authorization as false. It states that balances, assets, permissions, market availability and fee details remain UNKNOWN until independently verified.
- Added regression tests for inventory output, disconnected state, and excluding URL paths/query strings.
- This is only a reconnaissance primitive for the currently open page. It does not yet traverse all platform areas, inspect private account data, or wire a full audit into the cockpit. Do not claim those capabilities are complete.
- Safety: PAPER-only; no order submission, no REAL gate changes, no credentials or cloud resources.

### Next steps
1. Finish exact-head Python and Windows EXE/installer CI for the reconnaissance PR; inspect the final diff and merge only when all required checks are green.
2. Verify post-merge workflows on the resulting main SHA.
3. Continue toward a structured platform audit with explicit evidence states (CONFIRMED / UNKNOWN / BLOCKED / NOT_SUPPORTED) for account balances/assets, permissions, market types, order types, fees, limits, and execution/reconciliation capability. Use official authenticated APIs where available; browser inspection remains read-only and must not infer private account facts from UI labels.
4. Wire audit results to a user-visible dashboard only after the schema and source-of-truth semantics are tested.
5. Preserve human handling for MFA/CAPTCHA/anti-bot and any permission grants. Never request broad permissions merely to make a feature appear available. REAL remains behind existing independent gates.


## 51. Opportunity discovery, native platform tools, and capital ladder

### PR #314 — read-only browser reconnaissance merged
- PR: https://github.com/AndreVazao/VazaoSovereignTrader/pull/314
- Merge commit / resulting main SHA: `2261776ddaf989bb4b62b71c8362a9d16e0c8e44`.
- Exact PR head: `c911f16a6528b70e35c6a58b87babb1701d57707`; Python tests run 37010181701 SUCCESS and Windows EXE run 37010181970 SUCCESS.
- Post-merge Python run 37011986996 was IN_PROGRESS and Windows EXE run 37011987035 QUEUED at the time this context was edited; verify both on resulting main SHA before claiming post-merge CI passed.
- `PlaywrightPaperSurfaceAdapter.inspect_current_page()` inventories visible UI structure only. It is not a full site crawler and does not read balances, account assets, credentials, input values, cookies or storage.

### New opportunity/capital design
- Added `docs/OPPORTUNITY_DISCOVERY_AND_CAPITAL_LADDER.md` on branch `docs/opportunity-discovery-capital-ladder`.
- Scope: native exchange bots, copy trading, official promotions/rewards, fee reductions, eligibility, net economics, evidence statuses, and the owner's illustrative 1 -> 10 -> 100 -> 1,000 per-platform capital ladder.
- Treat reward codes and campaigns as time-limited and eligibility-bound; no assumption of daily guaranteed rewards. Prefer official sources and current in-account verification.
- Capital ladder is a configurable planning target, not an instruction to transfer/trade automatically. Account for fees/minimums, locked funds, open positions, custody/venue risk, transfer reconciliation and net equity.
- No duplicate/abusive reward claims, evasion of platform rules, fabricated codes, or use of extra accounts to bypass per-user limits. No real-money action solely because a balance target is reached.
- All new REAL trading, copy-trading, native bot activation, reward actions with economic obligations, and transfers remain behind explicit operator approval plus the existing readiness, preflight, Risk Engine, RealModeGuard, operator-authentication and reconciliation gates.

### Next steps
1. Finish post-merge Python and Windows EXE/installer workflows on `2261776ddaf989bb4b62b71c8362a9d16e0c8e44`.
2. Review and open a docs PR for `docs/opportunity-discovery-and-capital-ladder` content (branch name `docs/opportunity-discovery-capital-ladder`) after validating the complete diff.
3. Next implementation PR: typed opportunity schema/evidence states and unit tests; do not combine real trading or transfer execution into discovery work.
4. Continue one implementation PR at a time: official-source discovery, account/region eligibility, net-value calculations, dashboard shortlist, PAPER evaluation, then platform-specific adapters with explicit permission and reconciliation semantics.


## 52. Master roadmap and durable agreements — 2026-10-02

- Added on branch `docs/master-roadmap-continuity`: `docs/MASTER_ROADMAP_AND_AGREEMENTS.md`.
- This document consolidates the north-star objective, user agreements, safety rules, independent evidence dimensions, platform reconnaissance requirements, opportunity discovery, capital ladder, PAPER/REAL promotion policy, dashboard requirements, browser/desktop/Android boundaries, security/recovery expectations, repository workflow, implementation backlog and a copy/paste continuity prompt.
- Companion document: `docs/OPPORTUNITY_DISCOVERY_AND_CAPITAL_LADDER.md`, merged by PR #315.
- Main SHA verified before this documentation branch: `753b6f7a6b0eac3f1e1aa0b8a1e583429321cdad`.
- PR #315 merge SHA: `753b6f7a6b0eac3f1e1aa0b8a1e583429321cdad`. Exact-head Python workflow run 37012132630 reported SUCCESS. No post-merge workflow run was returned by the queried PR-run endpoint; verify current main CI before asserting all checks are green.
- PR #314 post-merge workflows were pending at the prior handoff and must be rechecked against current main before reporting complete.
- Scope remains documentation/continuity only. No trading, transfers, cloud provisioning, paid services, deployment or REAL activation were authorized.
- Next engineering step after this documentation PR: implement a typed opportunity schema/evidence-state model with provenance/expiry validation and unit tests; discovery must have no execution side effects.
- Keep this section synchronized with live GitHub after merge. Do not treat this branch's snapshot SHA as the future main SHA.


## 53. Opportunity registry implementation — 2026-10-02

- PR #316 merged: https://github.com/AndreVazao/VazaoSovereignTrader/pull/316
- Merge/resulting main SHA: `43eba2a94dd490e89b997300a422a8b7e62c15b0`.
- Exact-head Python tests for PR #316: run 37013424748 SUCCESS on `bad22836a43cbd87fc68e57f713479e2bb1afe8a`. The first run 37013306941 also succeeded on the prior head `2bf3ed54feb88d0b3db777d802307ed199a819e0`.
- Post-merge Python run 37013578362 on main SHA `43eba2a94dd490e89b997300a422a8b7e62c15b0`: SUCCESS.
- Post-merge Windows EXE run 37013578643 was still IN_PROGRESS at the time of this update; recheck before claiming all post-merge workflows are green.
- Current implementation branch/PR: `feat/opportunity-registry-schema`, PR #317 https://github.com/AndreVazao/VazaoSovereignTrader/pull/317 (not yet merged). Latest branch commit: `73fd762b7784043d0e78ab47da392d71878596c2` (docs update; verify live PR head before merge).
- Added `PC_ENGINE/opportunity/registry.py`: typed opportunity categories/statuses, validated status transitions, source provenance and timestamp checks, expiry handling, positive-net-estimate validation, append-only JSONL persistence, idempotent identical writes, and hard invariants `paper_only=true` / `execution_authorized=false`.
- Added `tests/test_opportunity_registry.py` for provenance, timestamp/state validation, expiry, no-action invariants, persistence, malformed JSONL rows and rejection of initial states other than DISCOVERED.
- Added `docs/OPPORTUNITY_REGISTRY.md`; updated the master roadmap's Track B and progress notes.
- No platform source ingestion, account probing, dashboard integration, transfer execution or REAL behavior is connected to this registry.
- PR #317 is already open; the latest safety fix requires a fresh exact-head CI run. Next: inspect the final PR diff and verify Python tests and Windows EXE/installer on the latest head; fix any failures before considering merge. Keep source allowlisting, automatic expiry sweeps and official ingestion for later steps.
