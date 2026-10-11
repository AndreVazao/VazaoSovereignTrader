# Sovereign Trader — Market Coverage and Edge Research
Date: 2026-10-11
Status: research checkpoint; no trading configuration or execution enabled.

## Executive conclusion
Build a multi-market research and adapter platform, not a bot that assumes a displayed price difference is profit. Prioritize public market-data feeds and official APIs, capture timestamped order-book evidence, estimate executable net edge, and keep a shadow/PAPER ledger. For cross-exchange crypto, start by evaluating spot pairs with inventory already present on both venues; do not rely on transferring coins after seeing a transient spread. Expand to FX only through a reviewed broker/API or demo interface. Mobile-app automation is a last-resort adapter, not the foundation of the trading core.

## Research findings

### 1. Cross-venue crypto arbitrage is real, but a screen-price gap is not an executable edge
- A 2025 peer-reviewed study using minute-level data across 16 crypto exchanges (2013–2024) finds that exchange-default risk, liquidity, transaction fees and blockchain congestion affect the persistence and usability of Bitcoin arbitrage opportunities. Transfers can be too slow/expensive to close the gap. Source: https://www.sciencedirect.com/science/article/pii/S154461232401393X
- A 2024 Review of Finance paper explains that settlement latency, volatility, transaction costs and price impact constrain crypto arbitrage; transferring assets exposes the strategy to price risk while waiting. Source: https://academic.oup.com/rof/article/28/4/1345/7609678
- A 2026 Journal of Banking & Finance study of realized CEX–DEX arbitrage reports operational costs, liquidity, market impact, competition and transaction-order uncertainty as practical constraints. Its reported historical returns are study-specific and are not a forecast for this project. Source: https://www.sciencedirect.com/science/article/pii/S0378426626000956
- A public 2026 research repository demonstrates an important backtest failure mode: reusing decision-time prices instead of the first executable quote after latency changed a preliminary profitable result into a loss. Treat this as an audit example, not a peer-reviewed universal result. Source: https://github.com/gustavosmede/btc-cross-exchange-arbitrage-research

**Design consequence:** distinguish (a) directional lead/lag prediction from (b) two-leg arbitrage. For two-leg arbitrage, model buy-side ask and sell-side bid at executable size, both fee schedules, slippage/market impact, partial fills, latency, inventory availability, funding/financing, and withdrawal/settlement friction. Only count a candidate if net edge remains positive under conservative latency/cost stress. If inventory must be transferred, include transfer time/risk and mark it as a different strategy class.

### 2. Use official market-data APIs before UI automation
- Binance's official Spot API documentation exposes REST, WebSocket market streams, order-book endpoints, testnet/demo material, and explicit rate-limit behaviour. Repeatedly ignoring 429/backoff can lead to IP bans. Sources: https://github.com/binance/binance-spot-api-docs and https://developers.binance.com/en/docs/products/spot/rest-api
- Kraken documents separate public market-data, private account and trading limits; limits are a real connector constraint, not an implementation detail. Source: https://support.kraken.com/gb/articles/206548367-what-are-the-api-rate-limits-
- Use these only as examples of the connector contract. Before enabling any venue, verify the exact current product, jurisdiction, fees, pair availability, API permissions and account terms. Public market-data keys and trading keys must be separate; default to read-only keys, no withdrawal permission, least privilege, local secret storage and revocation instructions.

### 3. Broader asset classes and practical order of work
1. **Crypto spot CEX-to-CEX:** first market family for multi-venue price/latency research; easiest to normalize through exchange APIs, but still subject to fees, depth, custody and venue risk.
2. **FX major pairs:** later, through a broker with an official API/demo environment. Include bid/ask spread, commission, financing/swap, market session, slippage, rejection and broker-specific execution. Do not assume a Forex/CFD app's displayed quote is directly comparable to a spot quote.
3. **Stocks/ETFs/index products:** later, after broker API/data permissions and market-hours/session semantics are supported. Exchange data may be delayed or subject to licensing; compare like-for-like instruments and currencies.
4. **Crypto DEX/CEX:** later research track. Include gas, pool depth/price impact, chain confirmation, MEV/front-running and bridge/counterparty risk; do not infer executable profit from AMM mid-prices.
5. **Mobile-only apps and web/desktop trading UIs:** classify as an integration target, not a market type. Prefer documented APIs. Use Android emulator/UI automation only after the platform's terms, account controls and stable test environment have been reviewed. UI screenshots/click timing are not a reliable market-data feed.

This is a prioritization proposal, not a claim that any one class currently offers a profitable strategy.

### 4. Portugal/EU regulatory and counterparty checks
- ESMA's 2025 consumer fact sheet says MiCA-authorised providers should be checked against ESMA and national regulator registers; services outside MiCA or other EU financial-services rules may offer limited or no consumer protection. Source: https://www.esma.europa.eu/sites/default/files/2025-10/Updated_Joint_ESAs_Factsheet_on_crypto-assets_IE_EN.pdf
- ESMA's 2026 notice says the MiCA transitional period ended on 1 July 2026 and unauthorised providers are expected to wind down in an orderly way. Verify provider status at the time of any future integration. Source: https://www.esma.europa.eu/?from_title=Documents&id=5238&page=document_details
- ESMA's 2026 risk report notes that leverage magnifies spreads, commissions and financing costs as well as market risk; it cites persistent losses among retail investors in leveraged barrier products. Source: https://www.esma.europa.eu/sites/default/files/2026-03/ESMA50-1949966494-4041_TRV_Risk_Monitor_1_2026.pdf
- This is engineering research, not legal advice. Before a platform can be enabled, verify current authorisation, product legal form, country availability, user account permissions and applicable terms.

## Recommended architecture for Sovereign Trader
1. **Connector registry:** each venue/platform declares asset class, instruments, data source, timestamp semantics, rate limits, fee source, supported order types, demo/testnet support, account/region availability and known restrictions.
2. **Canonical market-event schema:** venue + instrument identity, bid/ask/depth, exchange timestamp, local receive timestamp, sequence/update ID, source quality, latency and stale-data flag. Never conflate exchange time with local arrival time.
3. **Market capability map:** identify which venues can quote/trade the same economically equivalent instrument; handle symbol aliases, quote currency, contract multiplier, spot vs CFD/futures and session mismatch.
4. **Edge engine:** compute executable-size edge from bid/ask and depth, all known fees, conservative slippage/latency, currency conversion and inventory/capital constraints. Return NO_EDGE when fee, liquidity, timestamp or instrument comparability is unknown.
5. **Evidence and research layer:** log opportunities and counterfactual fills; run chronological holdout and walk-forward tests; report by venue pair, instrument, regime, latency/freshness, size and cost scenario. Prevent overlapping/correlated events from being counted as independent evidence.
6. **Capital/risk governor:** per-venue available balance, reserved inventory, max exposure, max daily loss, max order size, drawdown stop, venue-health gates and manual kill switch. A capital tier is a limit/goal, not an instruction to automatically deposit money.
7. **Execution boundary:** disabled by default, separate from research. When eventually approved, require idempotent client order IDs, explicit user authorization, test/demo evidence, order-state reconciliation and per-venue allowlists.
8. **Android/desktop UI adapter:** a local isolated worker may inspect the user's authorized apps, but it must not bypass MFA, captchas, platform safeguards or access controls. Use only where permitted and after API alternatives are exhausted; keep UI automation out of the latency-critical path.

## Capital ladder proposal
Do not automatically move from €1 to €10 to €100 to €1,000 just because every platform balance has reached a threshold. Balance is not evidence of safety or profitability. Treat each tier as a **review gate** requiring: adequate independent out-of-sample sample size, positive conservative net edge, stress-test survival, operational reliability, a verified legal/provider status, and a manual capital approval. Keep a separate reserve and never transfer/deposit funds automatically as part of strategy execution.

## Next implementation steps
- [x] Add per-relationship chronological OOS cost-stress diagnostics.
- [x] Add freshness/latency/horizon diagnostics and recorded-regime breakdown.
- [ ] Audit whether outcome samples overlap in time and add dependence-aware evidence / effective sample-size reporting.
- [ ] Define the canonical multi-asset instrument and connector capability schema.
- [ ] Build a read-only connector inventory and per-venue feature matrix; no credentials needed.
- [ ] Add a first API market-data adapter in read-only mode, selected after verifying the user's actual platform list and current regional support.
- [ ] Add a virtual per-platform ledger and tier-review gates before considering real capital.
- [ ] Revisit Android 16 app crash only after the market-data architecture is established.

## Safety status
Research/documentation only. No API keys requested, no exchange calls, no orders, no deposits/transfers, no paid AI services and no change to PAPER/REAL settings. Nothing in this document implies that a strategy is currently profitable.
