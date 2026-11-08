# Adaptive virtual office and cross-venue market research

**Updated:** 2026-11-08  
**Status:** product requirements recovered; visual expansion is deliberately secondary to brain/runtime readiness.

## 1. Product boundary

The virtual office is an observability and interaction layer for VazaoSovereignTrader. It must represent real backend tasks and verified states; it is not a simulation of work and is never the authority for trading decisions. The headless PC brain must continue when every visual client is closed, offline, minimized or unavailable.

The current Android office page is an offline demonstration. It is not connected to live agent/task state and must continue to label itself as a demo until a versioned runtime contract is integrated and physically tested.

## 2. Adaptive presentation

The client should choose a rendering profile based on measured device capability and observed performance, not merely the device model.

- **Chat-only:** minimum resource use; always available.
- **Compact / Palitinhos:** simple room and status presentation for low-memory phones and PCs.
- **Pixel / 8-bit:** recognizable office with low-detail assets and limited animation.
- **2.5D light:** richer rooms and navigation while preserving low CPU/RAM use.
- **HD 3D:** future optional tier only; never imply that a real 3D renderer exists before implementation and validation.

Manual selection and automatic selection should both be supported. A manual profile may fall back only when the device is unsafe or unable to sustain it, and the fallback must be visible. The mobile layout must be responsive and must not simply shrink a desktop building onto a portrait screen.

Reduce visual quality in this order under pressure: render resolution, effects, view distance, animation frequency, decorative detail, then fallback to a lighter mode or chat-only. Rendering pressure must never reduce the frequency or integrity of market-data collection, Radar, risk checks, persistence, reconciliation or PAPER bookkeeping.

When the app is in the background, stop continuous rendering and nonessential animation. Resume from authoritative backend state rather than replaying invented activity.

## 3. Truthful operational visualization

- A character may represent an agent only when it maps to a real, identifiable backend agent/task. Otherwise label it as decorative or demo.
- Movement, progress bars and room status must be driven by durable task events or current backend state.
- Show source, timestamp and freshness for market data, prices, latency, P&L and task results.
- Unknown, stale, disconnected, deferred and blocked states must remain explicit.
- Never fabricate prices, orders, P&L, approvals, agent counts, task progress or successful work to make the office look active.
- CEO remains the primary conversational entry point. Internal department views are navigation and reporting surfaces, not separate execution authorities.
- Existing/manual agents retain their established appearance; newly generated VST agents may use the approved robotic visual convention to distinguish their origin. Appearance never establishes identity or permission.

## 4. Logical department model

The office may expose logical rooms for:
- CEO / command and operator requests.
- Market Radar and public market data.
- Exchange comparison and venue capability research.
- Investigation and external evidence gathering.
- Analysis and strategy research.
- Central Memory / Learning Vault.
- Fast Response and incident handling.
- Risk and audit.
- PAPER Lab, replay and validation.
- Runtime, infrastructure and recovery.

A room does not imply a separate process, thread, agent or machine. The runtime registry is authoritative for which services actually exist. Rooms should expand only when corresponding capabilities and evidence are present.

## 5. Cross-venue market research

A price difference or apparent lead/lag is a hypothesis, not an executable edge. Before treating it as an opportunity, validate:

- Instrument equivalence: base/quote, spot versus derivative, contract multiplier, tick/lot size, index/mark/last price and venue-specific rules.
- Timestamp semantics: exchange event time, local receive time, monotonic time and decision time. Do not subtract unrelated wall clocks and label the result network latency.
- Feed integrity: sequence continuity, snapshot/delta recovery, freshness, gaps, reconnects, dropped messages and parser errors.
- Execution economics: fees, spread, depth, slippage, funding, borrow/financing, minimum order sizes and available capital.
- Statistical quality: sample independence, effective sample size, regime coverage, confidence intervals, multiple-testing bias and out-of-sample performance.
- Operational failure: API timeouts, partial fills, venue outages, stale books, rate limits and reconciliation.

Required research pipeline:
1. Discover candidate venues and instruments using public/read-only data.
2. Normalize instruments and venue capabilities without hiding exchange-specific semantics.
3. Measure data freshness, timing quality, spread, depth and feed integrity.
4. State a falsifiable hypothesis with entry, exit, invalidation and horizon.
5. Replay/backtest with realistic fees, spread, slippage, liquidity and latency.
6. Run live shadow/PAPER observation without real orders.
7. Validate on chronological out-of-sample periods and adverse regimes.
8. Review risk, capital, operational failure and reconciliation.
9. Record evidence and uncertainty; require explicit human approval and all existing gates before any later mode change.

The system must be allowed to conclude that an opportunity is not executable and do nothing. No strategy, visual indicator or aggregate score may auto-promote REAL.

## 6. Hardware adaptation and runtime separation

The visual client may adapt to CPU, RAM, GPU, screen size, thermal throttling, battery and measured frame performance. The backend separately adapts research concurrency and optional compute budgets. These are independent policies: reducing office detail must not pause or weaken the brain; increasing GPU capability must not increase trading permissions or risk limits.

On low-memory hardware, preserve continuous public Market Data, Radar heartbeat, durable observations, PAPER outcome persistence and critical telemetry. Defer optional historical studies and heavy visual rendering first.

## 7. Current state and gates

**Present:** offline Android office prototype, adaptive presentation labels, department concept, headless runtime, resource-aware backend job budgets and persistent task/learning components.

**Not certified:** live office-to-brain state binding, physical Android visual acceptance, full building renderer, HD 3D, remote mobile control, cross-venue profitability or live execution.

Acceptance gates:
- [ ] Versioned, authenticated state/event contract with snapshot recovery.
- [ ] UI shows only real backend tasks and source timestamps.
- [ ] Closing or crashing the UI has no effect on the headless brain.
- [ ] Low-memory profile remains responsive without interfering with market data or risk.
- [ ] Android portrait/landscape, zoom and room navigation are verified on a physical device.
- [ ] Background mode suspends expensive rendering and resumes from backend state.
- [ ] Every market opportunity report includes data quality, costs, uncertainty and out-of-sample evidence.
- [ ] PAPER-only behavior and existing REAL-mode gates remain unchanged.
