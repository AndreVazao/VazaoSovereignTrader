# VAZAO SOVEREIGN TRADER — PROJECT CONTEXT & CONTINUATION PLAN

Last updated: 2026-09-30 (UTC) — PR #225, #226, #227 and #228 merged; continuous PAPER study is now the active operational research task
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
Current main SHA after PR #228: 83e38a99848fa94c536a5a14ad0a7bb9133f2dc4.

Latest main validation observed:
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

## 9. Next actions

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

## 10. Active implementation — REAL readiness timing gate

Branch: feat/readiness-timing-gate

Implemented:
- REAL readiness requires a fresh WebSocket timing validation report by default;
- missing, stale or failed timing validation adds `websocket_timing_validation_required` to blockers;
- timing status is exposed in readiness output;
- configuration and documentation updated.

This is an additional fail-closed gate. It does not activate REAL or bypass any existing control.

## 10. Installation target

1. Install/prepare runtime.
2. Configure local API token.
3. Run verification.
4. Install automatic startup.
5. Reboot or start the two tasks.
6. Open local dashboard/cockpit.
7. Confirm PAPER engine and market-data collector are alive.
8. Leave the PC running continuously while evidence accumulates.

No live trading account is required for this first stage.

## 11. Continuity prompt

Continue working on AndreVazao/VazaoSovereignTrader. Read this file, verify live GitHub state, then continue the active branch/PR. Work autonomously on safe code. Keep exactly one active implementation PR where practical. Merge automatically when exact-head CI is green and review finds no blocker. Do not create cloud resources or incur costs without explicit authorization. The immediate objective is a reliable installable PAPER/data-collection node that can accumulate evidence for the trader's studies while all REAL gates remain fail-closed.
