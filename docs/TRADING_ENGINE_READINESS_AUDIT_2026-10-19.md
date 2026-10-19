# Sovereign Trader — Trading Engine Readiness Audit (2026-10-19)

## Executive summary

This is a repository/static audit checkpoint, not a live operational certification. It inspects the current `main` source tree and existing audit/roadmap evidence. No exchange credentials were used; no live orders or transfers were submitted; no Windows PC, Android device, or running engine was available for end-to-end validation in this audit.

**Current recommendation: continue in PAPER/shadow and read-only market research. Do not treat the system as REAL-ready yet.** The repository has substantial architecture and tests for risk, order identity, reconciliation, capital routing, research and mobile control. The remaining question is integration and fresh end-to-end evidence, not merely whether modules exist.

## Scope inspected

- `PC_ENGINE/core/engine.py`, `risk.py`, `real_mode_guard.py`, `order_manager.py`
- Capital routing/transfer policy, planner and execution bridge
- `docs/MASTER_ROADMAP_AND_AGREEMENTS.md`
- `docs/REAL_ACTIVE_EXECUTION_PATH_AUDIT_2026-10-07.md`
- `docs/REMOTE_MOBILE_SETUP.md`
- Repository tree inventory: engine, exchange adapters, radar/lead-lag, paper broker, transfer accounting/journal/reconciliation, Android app, workflows and relevant tests.

This audit does not claim every production call path or every test file was exhaustively executed.

## What already exists in source

1. **Engine and operating states:** `SovereignEngine`, runtime state, PAPER broker, startup mode handling, preflight, recovery, readiness, execution gate and REAL-mode guard are present.
2. **Risk and order path:** risk checks, exchange order rules, order manager, mandatory REAL authorization callback and deterministic client order identity are present.
3. **Recovery and accounting:** ledger, execution intents, pending-order reconciliation and capital-transfer journal/state/accounting/reconciliation components are present.
4. **Research infrastructure:** market radar, public market data bootstrap, websocket timing, lead/lag learning and validation, OOS/evidence/stress modules, regime and champion/challenger components are present.
5. **Capital ladder building blocks:** capital routing policy, venue discovery, planner, transfer intent, state, journal and execution bridge exist. The transfer bridge defaults disabled, requires explicit authorization and records SUBMITTED before external submission; ambiguous outcomes are represented as UNKNOWN_OUTCOME rather than blindly retried.
6. **Mobile/control surface:** Android app, pairing components, human bridge and remote setup documentation exist. Existence is not proof the APK starts reliably or remains connected remotely.
7. **Tests:** the repository contains broad targeted tests, including engine PAPER E2E, restart recovery, unknown outcomes, adapter contract, financial invariants, account reconciliation and transfer flows.

## Important prior evidence and limitations

The existing `REAL_ACTIVE_EXECUTION_PATH_AUDIT_2026-10-07.md` records a bounded audit of the primary order/transfer paths and reports targeted checks passing (8 passed, 7 deselected) plus `py_compile` and diff checks. It also explicitly records residual work: broader side-effect adapter coverage, crash timing around exchange acceptance/persistence, and audit of cancellation/withdrawal/transfer/browser/Android execution surfaces.

The same audit says the full account-reconciliation suite has stalled on Windows and must not be called green. A prior handoff also records that local test execution was inconclusive on a reconciliation test. These are open evidence gaps until a repeatable run completes on the exact current commit.

Remote PC-to-Android synchronization and the APK startup failure have not been proven resolved by this repository review. Do not infer that a generated debug APK equals a successful device smoke test.

## Readiness matrix

| Area | Repository evidence | Current status | Required next proof |
|---|---|---|---|
| Engine startup/state | Engine, preflight, watchdog and recovery modules | Implemented; runtime not proven here | Start/stop/restart PAPER on the target Windows PC; capture health and logs |
| Public market data | CCXT client, collector, radar and timing modules | Implemented in parts; venue-by-venue freshness not certified | Verify symbols, exchange/local timestamps, sequence gaps, stale-feed fail-closed behavior and reconnect recovery |
| Strategy/economic edge | Strategy, lead/lag, OOS, walk-forward and stress modules | Research capability exists; profitability not established | Reproducible out-of-sample results net of fees, spread, slippage, funding, latency and transfer costs; confidence/sample-size reporting |
| Risk and REAL gates | RiskEngine, RealModeGuard, ExecutionGate, readiness/preflight | Guards exist; no REAL certification | Full current-commit caller inventory and negative tests for every side-effect route |
| Order lifecycle | OrderManager, client IDs, intents, reconciliation | Design exists; complete current end-to-end proof missing | Test accepted-but-timeout, partial fill, cancel race, restart and ambiguous client-order lookup without duplicate submission |
| Capital routing | Policy/planner/transfer ledger and bridge | Planning code exists; real transfers must remain disabled | Simulated ladder tests; fee/network/minimum/reserve checks; unknown outcome and restart tests; separate approval for each real transfer |
| Persistence/ownership | OwnerContext, ledger and owner-bound stores | Components exist | Verify multi-user/family isolation, single-writer assumptions, crash durability and no cross-owner state leakage |
| Mobile cockpit | APK, pairing and remote setup docs | Not device-verified; startup/UX issue remains open | Capture Android logcat/startup result; test pairing, token revocation/expiry, reconnect, alert delivery and safe action acknowledgement |
| PC 24/7 | Autostart/watchdog/recovery components | Designed; not verified on the actual PC | Restart after OS reboot, network loss and process crash; verify recovery and no duplicate side effects |
| CI/test evidence | Python, Windows EXE and Android workflows exist | Workflow existence is not a pass | Run allowed/manual workflows on the exact audit head and retain run IDs, artifact SHA and logs |

## Capital ladder: convert the user's idea into a safe state machine

The intended ladder is: prove one venue first; keep its protected baseline; only allocate small, bounded surplus to the next approved venue; grow venue allocations through explicitly configured tiers (e.g. 10 → 100 → 1,000 quote units) only after evidence and reconciliation. Do not hard-code a promise that every venue will receive funds or that larger stakes guarantee larger profits.

Before any live transfer is considered:
- Maintain a durable, reconciled per-venue baseline, cash balance, equity, fees, unsettled funds and reserve.
- Distinguish **profit**, **available cash**, **withdrawable/transferable balance**, and **deployable capital**.
- Propose transfers only where a verified destination opportunity justifies them after network fees, exchange fees, minimums, settlement time, slippage, inventory and risk limits.
- Require an allowlisted same-owner destination and exact asset/network compatibility.
- Persist intent/idempotency key and SUBMITTED state before the external call; UNKNOWN_OUTCOME must trigger reconciliation, not retry.
- Require a fresh, explicit operator approval for each real transfer; a profit threshold or ladder tier must never grant REAL permission.
- Keep withdrawal permission disabled by default. Transfers and trading orders are different action types with independent authorization.
- Start with one venue's public data and PAPER/shadow. Expand venues only when the adapter, market equivalence and operational readiness are verified.

## Priority order

### P0 — establish a reproducible baseline
1. Identify the exact current `main` SHA and current workflow status.
2. Run targeted PAPER engine tests and adapter-contract tests on that exact SHA.
3. Re-run the account reconciliation and restart/unknown-outcome tests in a bounded environment; if a run hangs, capture the exact test and logs and report inconclusive rather than green.
4. Collect a real Windows PC startup/health report and Android startup/logcat evidence. Until then, label PC/phone integration unverified.

### P1 — close financial side-effect gaps
1. Inventory all reachable order, cancel, transfer, withdrawal, browser, and Android routes.
2. Test every route's authorization boundary and fail-closed behavior.
3. Add crash-injection tests at each boundary between durable intent, external acceptance, response parsing, persistence and reconciliation.
4. Prove duplicate prevention and exact owner isolation under concurrent/restarted operation.

### P2 — establish a trustworthy research loop
1. Run read-only venue discovery and market-data collection for one liquid venue first.
2. Validate timestamp semantics, stale/gap handling, symbol/contract equivalence and realistic cost models.
3. Produce chronological OOS/walk-forward and stressed-cost reports, with sample sizes and uncertainty.
4. Keep signals observational/PAPER until results are reproducible and robust; do not promote automatically to REAL.

### P3 — mobile as a dependable remote cockpit
1. Fix the startup failure from actual traceback/logcat, not speculation.
2. Verify private-network pairing and authentication, token rotation/revocation, request expiry and reconnect semantics.
3. Make task/approval requests durable and visible remotely; unknown action outcome must be reconciled before retry.
4. Never accept passwords, API secrets, MFA codes or recovery codes in ordinary chat/history/logs.

### P4 — capital allocation and office visualization
Implement the ladder in PAPER simulation first. The future office floors (top command/brain, research and exchange levels, vault basement) are a view over verified backend state, never a control plane or financial ledger. Money carts/flows are illustrative only unless tied to a confirmed transfer event. A 1D/low-resource view should use simple moving markers and minimal rendering; it must not affect engine cadence or phone battery unnecessarily.

## Definition of done before any REAL pilot

- Current-commit tests complete and green, including account reconciliation and adapter contracts.
- Windows EXE startup, PAPER operation, restart recovery and safe shutdown verified on the intended PC.
- Market-data freshness and fail-closed behavior verified with real public data, no trading credentials required.
- No unresolved order/transfer intents; duplicate prevention and UNKNOWN_OUTCOME recovery proven.
- Current execution-path inventory covers order placement, cancel, transfer and any other financial side effect.
- Mobile pairing, authentication, remote alerts and action acknowledgements verified on a real device.
- Independent explicit operator authorization, strict risk limits, least-privilege exchange keys and withdrawals disabled.
- A separate reviewed decision approves any live pilot. Passing tests or reaching a capital tier is not permission.

## Final assessment

The project is not starting from zero; there is meaningful engineering in place. The blocking issue is proving that the pieces compose reliably on the actual PC and phone, and that financial side effects remain safe through failures. Prioritize operational evidence and bounded PAPER runs before adding more strategies, more exchanges, the vault animation, or REAL capital.
