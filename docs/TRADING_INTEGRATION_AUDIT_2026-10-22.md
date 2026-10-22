# VazaoSovereignTrader — Integration Audit 2026-10-22

## Audit identity and limits

- Audited repository: AndreVazao/VazaoSovereignTrader.
- Main checkpoint before this audit document: 93b2559ef300bc1c0700eb9bca2c20fcb6d9af40 (merge of PR #429).
- Scope: static source/config/documentation inspection plus review of available GitHub CI evidence. This is not a live runtime, exchange, Windows PC, Android device, or profitability certification.
- Recent exact-head CI evidence: PR #429 head 96df885caa2bcca6916e3c2883c3eab394740898, Python workflow run 39732769193 / #3031, job 119671371199 — full Python suite passed. Snyk and Vercel checks passed on that PR head. CodeRabbit posted that automatic review is not enabled for this repository unless explicitly triggered; its green status is not counted as an independent code review. No real exchange connection, credentials, order, transfer or local-device test was performed for this audit.
- Status vocabulary: CONFIRMED IN SOURCE = the named source/test supports the claim; PARTIAL = some components exist but integration/evidence is incomplete; BLOCKER = must be resolved before claiming the corresponding capability is ready; NOT VERIFIED = requires a runtime/device/build or other evidence not available here.

## Executive conclusion

The repository contains substantial trading, research, risk, accounting, remote-control and mobile code. The key gap remains proving that the components work together on the target PC and phone with the exact effective configuration and that all side-effect routes remain protected under failure/restart.

**Recommendation: remain PAPER / read-only. Do not treat the project as REAL-ready.** The latest Python suite is green on the exact PR #429 head, but this does not prove real-device startup, live venue connectivity, complete economic edge, or production-safe real-money execution.

## Coverage matrix

| Area | Status | Source evidence / finding | Required proof or next action |
|---|---|---|---|
| Engine startup and operating state | PARTIAL | PC_ENGINE/core/engine.py contains SovereignEngine, PAPER startup normalization, preflight, recovery, readiness and execution state. | Run startup/stop/restart on the intended Windows PC; collect health/log evidence for reboot, process crash and network loss. |
| Market data — primary trade radar | PARTIAL | PC_ENGINE/radar/websocket_radar.py supports public Binance, Coinbase and OKX trade streams, deduplication, connection/message errors and freshness telemetry. PR #426 moved its OKX endpoint to wss://ws.okx.com/ws/v5/public. | Verify actual connection/subscription, symbol mapping, reconnect and freshness on public feeds; do not infer one-way latency from uncalibrated exchange timestamps. |
| Market data — top-of-book | PARTIAL | PC_ENGINE/market_events/websocket_collectors.py emits public ticker observations. PR #428 changed the OKX endpoint and added test_default_okx_public_endpoint_uses_tls_443. | Verify valid bid/ask, positive prices, bid < ask, freshness, timestamp quality and behavior under malformed/stale feed. This is top-of-book observation, not a full depth book. |
| Market data — L2 depth | PARTIAL / BLOCKER for depth-based signals | PC_ENGINE/market_events/l2_collectors.py parses snapshot/delta-like events; PR #429 changed the OKX endpoint and added test_default_okx_l2_endpoint_uses_tls_443. Parsing events is not the same as maintaining a synchronized local order book. The OKX collector subscribes to books5, while parser sequence assumptions must be verified against the exact current channel schema. | Build/test a protocol-specific book state machine with snapshot synchronization, sequence continuity, gap invalidation/resync, stale-data fail-closed behavior and bounded buffers. Do not use current L2 output as a verified book until this is done. |
| OKX endpoint coverage | CONFIRMED for three identified runtime config generators | Current main files checked: PC_ENGINE/radar/websocket_radar.py, PC_ENGINE/market_events/websocket_collectors.py and PC_ENGINE/market_events/l2_collectors.py all now use wss://ws.okx.com/ws/v5/public. PRs #426, #428 and #429 each add coverage for a separate consumer. | Keep endpoint regression tests in all three paths or centralize endpoint configuration in a single tested source. This check covers the three identified consumers, not a guarantee that every possible script/config in the repository was exhaustively enumerated. |
| Exchange coverage | PARTIAL | Native low-latency WebSocket radar supports Binance/Coinbase/OKX. The example config lists other venues for REST/bootstrap/research, including BingX and Bybit, but does not establish native WebSocket temporal coverage for all of them. | Inventory every exchange adapter and distinguish REST polling, trades, ticker, L2, derivatives, supported symbols and verified capabilities. Add venues one at a time with contract tests. |
| Symbol/instrument equivalence | NOT VERIFIED end-to-end | Different venues use different symbol conventions and products; the available source inspection does not prove universal spot/contract equivalence across all configured venues. | Explicitly normalize base/quote, spot vs perpetual, contract size, settlement currency, precision and venue market identity before cross-venue comparison. Reject non-equivalent instruments. |
| Timing / lead-lag | PARTIAL | Radar and learning modules preserve venue/local timestamps and reject some invalid temporal candidates. Fast-path bridge rejects events when calibrated latency is unknown. | Establish clock-offset calibration, separate monotonic receive ordering from wall-clock estimates, test stale/reordered events, and prove results out-of-sample after fees/spread/slippage/funding/latency. No profitable edge is established by the existence of signals. |
| Order-book continuity | BLOCKER for depth-based edge | docs/SOVEREIGN_MARKET_RADAR.md now records Binance diff-depth + snapshot rules and OKX sequence/checksum notes. No claim is made that the full book reconstruction is implemented. | Implement isolated state machine and deterministic tests for initial snapshot, duplicate/old updates, contiguous update, gap, reconnect, buffer overflow and recovery. Never use trade IDs as depth sequence IDs. |
| Strategy / confluence / derivatives / candles | PARTIAL | Example config includes technical, candlestick, confluence, lead-lag, derivatives and regime-related research settings; several are explicitly observational/PAPER. | Verify actual runtime wiring for each feature, missing-data behavior, independent evidence count, stale gates and ablation tests. Measure chronological walk-forward/OOS performance and uncertainty; no strategy profitability is proven here. |
| Research and shared learning | PARTIAL | Local learning/evidence artifacts exist. Example shared_intelligence config uses LOCAL_ARTIFACTS and has sync_enabled=false; Vercel is listed as optional provider but not enabled by that example. | For the intended multi-computer learning, verify artifact schema/version, provenance, validation status, ownership/privacy filters, dedupe, conflict handling, signing/integrity, opt-in sync and offline behavior. Do not sync balances, positions, credentials or owner-private data. |
| Risk / execution gates | PARTIAL; no REAL certification | PC_ENGINE/core/engine.py, risk.py, real_mode_guard.py, execution_gate.py and order_manager.py provide separate guard layers. docs/REAL_ACTIVE_EXECUTION_PATH_AUDIT_2026-10-07.md records the intended guarded path and prior targeted evidence. | Re-run a current-commit caller-path inventory and negative tests for every order/cancel/transfer/withdrawal/browser/mobile side-effect route, including race conditions and failures. Prove each adapter is unreachable when gates deny. |
| Effective REAL configuration | BLOCKER to any deployment claim until checked on target PC | At the audited base SHA, config.example.json had autonomous_execution enabled=true, allow_real=true and auto_promote_real=true. This follow-up PR changes the example to allow_real=false and auto_promote_real=false while preserving PAPER autonomous research; that does not change any existing config.local or prove the effective runtime policy. | After merging, inspect the effective private configuration on the PC without exposing secrets, confirm the operator's intended policy, and test that startup remains PAPER and no promotion can occur without the required explicit authorization and all fresh gates. |
| Order lifecycle / crash recovery | PARTIAL | OrderManager, execution intents, deterministic client order identity, pending reconciliation and UNKNOWN_OUTCOME handling exist; prior audit documents describe fail-closed recovery. | Run current-head controlled-adapter E2E for accepted-but-timeout, partial fill, cancel race, crash between external acceptance and persistence, restart, duplicate prevention and ambiguous lookup. Confirm full account reconciliation has a repeatable current-head result; historical local Windows stalls remain a known evidence gap even though current hosted Python CI passed. |
| Capital allocation / transfers / accounting | PARTIAL | Capital transfer execution, journal, accounting and reconciliation modules/tests exist; prior audit describes explicit authorization and UNKNOWN_OUTCOME not being blindly retried. | Prove production wiring from authoritative owner/risk/readiness policy to every transfer adapter; test asset/network/minimum/fee/reserve, wrong owner, duplicate idempotency key, crash and venue verification. Keep transfers disabled unless separately authorized. |
| Owner isolation / financial privacy | PARTIAL | OwnerContext and owner-bound storage/auth components exist; config example defines multiple owners and scopes. | Run cross-owner negative tests across API, balances, positions, orders, artifacts, shared learning, logs, transfer destinations and concurrent processes. Never infer isolation merely from configuration entries. |
| API / remote control | PARTIAL | PC_ENGINE/api/server.py exposes authenticated routes and a public /health probe; private state/commands require token/scope checks. Example binds host 0.0.0.0 and token comes from environment. | Verify effective bind/firewall/private network, token expiry/rotation, least-privilege scopes, replay resistance, audit log redaction, and each route's authorization. Public health proves reachability only, not authorization. |
| Android pairing / LAN + Tailscale | PARTIAL; physical device NOT VERIFIED | docs/ANDROID_FIRST_PAIRING.md and docs/ANDROID_LAN_TAILSCALE_IMPLEMENTATION_CONTRACT.md describe expiring pairing, revocation, Keystore token storage, separate LAN/Tailscale routes and GET-only failover; mutating requests are not replayed. | Physical Android validation remains required: APK launch/logcat, Keystore/OEM behavior, pairing/revocation, reconnect across home Wi-Fi/Tailscale, 401/403 and no duplicate POST. No live device evidence was collected here. |
| APK / Windows EXE / install/autostart | NOT VERIFIED on current audit SHA | Historical workflows and docs record earlier build/smoke evidence, but that is not evidence that current main 93b2559ef300bc1c0700eb9bca2c20fcb6d9af40 is built, installed and running on the user's PC/phone. | Run current-head Windows EXE/installer and Android APK workflows where available, record artifact SHA, then perform real-device/PC smoke and reboot recovery. |
| Virtual office / cockpit | PARTIAL / design-level | Architecture docs describe a headless engine and independent observation/control UI; existence of docs does not prove a complete working virtual office connected to live backend events. | Keep the engine authoritative. Verify each room/department reflects real API state, actions use the same authorization boundary, chat-only fallback works and animations never invent fills/transfers. |
| CI and review evidence | CONFIRMED for latest Python PR head; PARTIAL overall | PR #429 exact head passed full Python workflow 39732769193, job 119671371199; Snyk and Vercel passed. CodeRabbit status was green but CodeRabbit said automatic reviews are not enabled without a trigger. | Recheck post-merge main statuses and run current-head Windows/Android builds. Keep manual diff review separate from automated status labels. |

## Prioritized action list

### P0 — deployment safety and integration proof
1. Inspect the effective configuration on the actual Windows PC before any live use; the example file opts into autonomous REAL promotion flags even though guard layers also exist.
2. Produce a current-main caller graph for order placement, cancellation, transfers, withdrawals and all browser/desktop/Android surfaces. Include negative tests for every adapter side effect.
3. Confirm PAPER startup, SAFE_MODE persistence, restart recovery and authoritative account reconciliation on the intended PC.
4. Run Windows EXE/installer and Android APK workflows on the current audit SHA; follow with real PC/device smoke tests. Hosted CI is not a substitute.

### P1 — finish market-data contracts
1. Complete an inventory of every endpoint/config generator and exchange capability; avoid duplicate configuration drift by centralizing endpoint constants where appropriate.
2. Implement a real protocol-specific local L2 state machine, starting with one venue/channel and tests before adding more venues.
3. Validate timestamp calibration, instrument equivalence, freshness, reconnect and gaps; unknown continuity must make a book ineligible for edge calculations.
4. Keep BingX/Bybit and derivatives coverage labeled by actual capability (REST/ticker/trades/L2/funding/OI), not by planned configuration.

### P2 — prove the research edge
1. Run PAPER/shadow with reproducible data collection and integrity checks.
2. Evaluate chronological walk-forward/OOS performance, sample size, confidence intervals and stress costs.
3. Include fees, spread, slippage, funding, inventory, transfer costs and execution delay.
4. Keep candidate discovery separate from authorization; a high score or learned artifact must never authorize execution.

### P3 — multi-device learning and cockpit
1. Keep shared learning artifacts aggregate, versioned, provenance-tagged and owner-private-data-free.
2. Enable Vercel sync only after explicit design/permission and tests; current example config has sync disabled.
3. Verify PC/phone authentication, remote alerts, durable approvals, reconnection and no mutating-request replay.
4. Treat virtual office as a UI over verified backend state, never a ledger or execution authority.

## Audit exit criteria

This audit is complete as a static evidence checkpoint, not a production readiness sign-off. Before any REAL pilot, every P0 item must have fresh evidence on the exact release SHA, all unresolved side-effect paths must fail closed, market-data continuity must be explicit, and the operator must separately approve the release. Green unit tests, a successful deployment preview, or reaching a capital tier is not permission to trade real money.

## Evidence references

- Latest main checkpoint: 93b2559ef300bc1c0700eb9bca2c20fcb6d9af40.
- PR #426 (primary OKX radar endpoint): https://github.com/AndreVazao/VazaoSovereignTrader/pull/426.
- PR #428 (top-of-book OKX endpoint): https://github.com/AndreVazao/VazaoSovereignTrader/pull/428.
- PR #429 (L2 OKX endpoint): https://github.com/AndreVazao/VazaoSovereignTrader/pull/429.
- Previous trading readiness audit: docs/TRADING_ENGINE_READINESS_AUDIT_2026-10-19.md.
- Previous execution path audit: docs/REAL_ACTIVE_EXECUTION_PATH_AUDIT_2026-10-07.md.
- Mobile pairing and remote route contracts: docs/ANDROID_FIRST_PAIRING.md and docs/ANDROID_LAN_TAILSCALE_IMPLEMENTATION_CONTRACT.md.
- Market radar and order-book protocol notes: docs/SOVEREIGN_MARKET_RADAR.md.


## Follow-up after audit — safer example defaults

The audit identified that the checked-in example enabled autonomous REAL promotion flags. The follow-up change keeps autonomous PAPER research enabled but sets `autonomous_execution.allow_real=false` and `autonomous_execution.auto_promote_real=false` in `PC_ENGINE/config/config.example.json`, with a regression test in `tests/test_fast_path_config.py`. This is defense-in-depth for new setups only: it does not edit or inspect a user's existing `config.local.json`, does not certify startup behavior on the target PC, and does not replace the separate human authorization and engine-side gates.


## Follow-up after PRs #433–#437 (2026-10-22)

### Evidence now present on main
- Binance Spot depth has a fail-closed state machine plus a collector integration that fetches a public REST snapshot, buffers/replays WebSocket diff-depth updates, invalidates on sequence gaps/overflow/disconnect, reconnects with backoff, and emits a separate synchronized-view JSONL plus current health/freshness JSON. This remains observational and is **not** connected to edge/signal or order execution.
- The office now reports truthful connection state, sends validated department context, maintains session-only per-department chat history, and calls read-only handlers for venue health, market-data health, research queue, PAPER evidence, readiness, recovery, evidence ledger and human-interaction counts. These are deterministic handlers, not independent autonomous agents. Durable conversation history and browser/device E2E are not yet proven.
- Mobile startup contract/syntax tests and Buildozer APK build passed on PR #437 exact head. A local startup diagnostic fallback and Kivy status-widget re-parenting fix are merged. The reported immediate crash is not definitively diagnosed until the APK is launched on a physical Android device and logcat is inspected.

### Current follow-up in PR #438
- The example config removes `trade_real` from default owner scopes while preserving PAPER mode, `allow_real=false` and `auto_promote_real=false`.
- The Windows EXE/installer workflow now runs on relevant pull requests and adds a real silent-install → installed EXE `/health` smoke → silent uninstall/task cleanup sequence. This workflow must pass before claiming the installer is validated.

### Remaining release blockers
1. Effective `config.local.json`, environment tokens, firewall, scheduled tasks and paths on the user's actual PC remain unverified. An example config or CI runner is not evidence of the local setup.
2. Physical Android launch, authentication, reconnect, layout/status-bar behavior and logcat remain unverified; APK build success is not phone readiness.
3. OKX and Coinbase do not yet have protocol-specific synchronized books. Their raw L2 JSONL must not be used as a book.
4. Cross-exchange instrument equivalence, edge-after-fees/slippage/latency proof, and signal-to-execution/reconciliation integration remain incomplete.
5. Independent department workers, server-persistent per-department history, browser E2E, Tailscale/LAN failover, and virtual-office hardware-adaptive rendering remain incomplete.
6. Keep PAPER/read-only; no REAL execution or live trading claim until separate gates are tested.

### Updated heuristic readiness estimates (not automated metrics)
- Engine + public data collection: 78%.
- Cross-exchange temporal edge: 48%.
- Security / execution / reconciliation integration: 60%.
- Virtual office / cockpit: 65% (read-only handlers and session context exist; independent agents and E2E do not).
- Android APK: 35% (debug APK build passes; physical launch unverified).
- Windows installer/current PC: 40% (CI smoke added in PR #438; local PC state unverified).


## Current-main checkpoint after PR #438 (2026-10-22)

- Current product main at checkpoint: `5cd14a69d707e2cb935e7d9da621aa6888901068` (PR #438 merged).
- PR #438: https://github.com/AndreVazao/VazaoSovereignTrader/pull/438 — merged after review of the diff and successful exact-head CI.
- Python workflow run `39745494853`: completed successfully on PR head `77ef30ce6e10324dad160e34123aff752aa951e7`.
- Windows EXE workflow run `39745494861`: both `build-exe` and `build-installer` jobs completed successfully on that exact head. The installer smoke checks silent install, installed files/config, both scheduled tasks, PAPER launch with loopback-only health probe, process stop, silent uninstall and scheduled-task cleanup.
- This is hosted Windows-runner evidence only. It does not establish that the user's PC has the same effective private config, environment, firewall, scheduled tasks or a healthy installed runtime.
- PR #439 separately removed `trade_real` from `DEFAULT_OWNER_SCOPES`; absent/empty owner scopes now remain least-privilege by default. The example owner scopes were also cleaned in #438. Existing local config and previously issued tokens were not inspected or revoked by these changes.
- The installer workflow now looks for the versioned Inno Setup output (`VazaoSovereignTrader-Setup-*.exe`) and requires exactly one candidate, avoiding the previous mismatch between versioned build output and an unversioned expected filename.
- The current-main source includes Binance Spot book synchronization work beyond the earlier baseline described above: REST snapshot acquisition, buffering/replay of diff-depth events, sequence-gap/overflow/disconnect invalidation, reconnect backoff, and a separately emitted synchronized-view artifact/health record. Treat this as observational only; it is not evidence that the book is connected to the temporal-edge calculator or execution path. OKX/Coinbase protocol-specific synchronized books and cross-venue edge-after-cost proof remain blockers.
- The historical percentages above are rough engineering estimates, not measured reliability. In particular, Windows CI release-smoke confidence has improved, but **actual PC readiness remains unverified**; Android physical launch/logcat remains unverified.
- Operational posture remains PAPER/read-only. No live order, transfer, withdrawal, or REAL activation was performed.

### Next acceptance gates
1. On the actual Windows PC, inspect effective mode, owner scopes, REAL flags, token sources, bind address/firewall, scheduled tasks and health/log output without copying secrets into GitHub or chat.
2. On a physical Android device, capture launch/logcat evidence and verify status-bar-safe layout, authentication, reconnect, revocation and LAN/Tailscale transitions; never replay a mutating request on failover.
3. Before depth-based edge evaluation, add protocol-contract tests and explicit wiring evidence for Binance synchronized views; implement separate OKX/Coinbase synchronization or keep those venues ineligible for depth signals.
4. Prove normalized instrument identity and net edge after fees, spread, slippage, funding, latency, inventory and failure costs using chronological out-of-sample PAPER/shadow evaluation.
5. Keep independent office agents, persistent department conversations and browser E2E labelled incomplete until runtime evidence exists.


## Addendum — latest main and market-data changes (2026-10-22)

- Latest main reviewed for this addendum: `29f93b642df6f2949693e688f06ff4aea4ca2140`.
- The Binance Spot depth state machine now has explicit publication of book invalidation states and regression coverage (latest main commit message: `fix(market-data): publish Binance book invalidation states`). This improves observability when a book becomes unusable; it does not itself prove snapshot/delta continuity under live exchange traffic, nor does it authorize the book as an input to the edge calculator.
- PR #442 is open, not merged, and proposes a Coinbase Advanced Trade L2 parser correction: handle inbound `l2_data` envelope, preserve `sequence_num`, validate `product_id`, and reject unsupported event forms. Until that PR is reviewed, CI-validated and merged, do not count this parser fix as part of main. Even after merge, parser correctness is not full Coinbase book synchronization.
- PR #443's earlier documentation branch was closed because main advanced while it was open. This addendum is being submitted from a fresh branch based on the latest main to avoid stale-base ambiguity.
- No live venue connection, private credential, physical device, live order or profitability test was performed during this source/CI review. Keep the system in PAPER/read-only.


## Addendum — latest main and market-data changes (2026-10-22)

- Main checkpoint reviewed: `29f93b642df6f2949693e688f06ff4aea4ca2140`. Main has moved since the earlier PR #438 checkpoint, so use this addendum as the more recent status.
- Binance Spot synchronization code is fail-closed and exposes explicit book status/eligibility. The implementation checks update sequence ranges, rejects gaps and malformed levels, removes zero-quantity levels, and invalidates stale/invalid state. The runtime collector handles snapshot acquisition, buffered deltas/replay, overflow/disconnect invalidation, reconnect backoff, and publishes a separate synchronized-view artifact/health record.
- Recent main commit `29f93b6` publishes Binance book invalidation states so downstream observers can see invalidation rather than silently retaining a prior healthy view. This improves observability, but does not prove the synchronized view is wired into temporal-edge scoring or execution. Do not treat the feed as trade-eligible until that wiring is explicit and tested end-to-end.
- PR #442 addresses a Coinbase Advanced Trade parser contract: inbound `l2_data` envelope, `sequence_num`, configured `product_id` validation, envelope timestamp fallback, and unknown-event rejection. It remains a parser/telemetry improvement only; it does not establish a synchronized Coinbase book.
- The previous documentation PR #443 was closed unmerged after the base branch advanced; the audit changes are being consolidated in this branch to avoid leaving a stale duplicate PR open.
- Vercel reported deployment rate limiting on the audit branch. This is an external deployment quota status, not a Python test failure; the audit is documentation-only and does not require a Vercel deployment for runtime correctness.
- Readiness must remain separated into (a) code/CI evidence and (b) actual device/runtime evidence. Hosted Windows installer smoke passed on the exact PR #438 head; user PC effective configuration and runtime are still unverified. Android physical launch/logcat and end-to-end LAN/Tailscale behavior are also unverified.
- Trading posture remains PAPER/read-only. No live order, transfer, withdrawal, or REAL activation was performed.

### Updated acceptance gates
1. Keep Binance depth ineligible for any edge/execution path until a deterministic integration test proves the exact synchronized-view consumer, freshness rejection, sequence-gap invalidation and recovery.
2. Complete Coinbase and OKX protocol-specific book synchronization and tests before comparing their depth; never apply Binance sequence rules to other venues.
3. Validate normalized instrument identity and calculate net edge after fees, spread, slippage, funding, latency, inventory and failure costs with chronological out-of-sample PAPER/shadow evaluation.
4. On the actual Windows PC, verify effective mode, owner scopes, REAL flags, token sources, bind address/firewall, scheduled tasks and health/log output without exposing secrets.
5. On physical Android, verify launch/logcat, status-bar-safe layout, authentication, reconnect, revocation, and LAN/Tailscale transitions; failover must not replay mutating requests.
6. Continue labelling independent autonomous office agents, persistent per-department conversations and browser E2E as incomplete until implementation and evidence exist.
