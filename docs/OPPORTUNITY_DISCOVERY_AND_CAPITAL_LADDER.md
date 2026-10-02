# Opportunity Discovery and Capital Ladder

## Purpose

The Sovereign Trader should systematically discover legitimate, accessible ways to improve net portfolio outcomes across the owner's already-authorized exchange accounts. This includes native exchange automation, copy trading, promotions/rewards, fee reductions, research tools, and the project's own PAPER-tested strategies. Discovery is not an endorsement and does not imply a positive expected return.

## Opportunity classes

1. **Native automation:** exchange-provided grid/DCA/rebalancing and other bots. Record supported market, strategy parameters, funds/account compartment, fees, stop conditions, API/UI control options, and known failure modes.
2. **Copy trading:** supported lead/copy portfolios and eligible markets. Record full history length, net return where available, drawdown, volatility, leverage, concentration, fees, follower restrictions, exit mechanics, and data quality. Win rate alone is insufficient.
3. **Rewards and promotions:** official campaign announcements, vouchers, red packets, quests and fee rebates. Record official source, campaign start/end, region/account eligibility, quota/availability, asset, claim steps, expiry, withdrawal/use restrictions, and any required deposit/trading/holding/referral action. Never treat a past campaign or a social-media code as a current guaranteed reward.
4. **Cost reduction and research:** fee tiers, rebates, supported data endpoints, market scanners, funding/borrow costs, and official learning or strategy marketplaces.
5. **Native APIs and authorized automation:** prefer official documented interfaces with least-privilege permissions. UI automation is a fallback for permitted interactions, not a method to evade restrictions.

## Opportunity record and evidence states

Every candidate should have: venue/account scope; discovery timestamp; official source URL and capture timestamp; feature category; region/KYC/eligibility conditions; requirements and estimated costs; gross reward or return claims; independently verifiable net economics; risk and liquidity notes; automation method; required permissions; expiry; test status; and recommendation rationale.

Use explicit states:
- `DISCOVERED`: found, not verified.
- `ELIGIBILITY_UNKNOWN`: account/region access not confirmed.
- `ELIGIBLE_CONFIRMED`: eligibility supported by current account or official evidence.
- `NET_VALUE_POSITIVE_ESTIMATE`: only an estimate, not a guarantee.
- `PAPER_TESTED`: tested without real funds.
- `READY_FOR_EXPLICIT_APPROVAL`: preconditions reviewed; no action yet.
- `CLAIMED_OR_ENABLED_CONFIRMED`: platform confirms the action and result.
- `EXPIRED`, `BLOCKED`, `UNSUPPORTED`, `REJECTED_BY_POLICY`, `UNKNOWN_OUTCOME`.

Do not label a campaign or strategy profitable based only on advertised APY, historical leaderboard, win rate, a gross reward amount, or a referral post. Calculate expected net value after trading fees, funding/borrow costs, spreads, slippage, transfer/network fees, lockup, tax/accounting considerations, and downside risk where estimable. Explicitly mark unknowns.

## Binance investigation notes

Official Binance support documents describe a Trading Bots Account and native Spot Grid / Futures Grid tools; exact features, eligible products and limits can vary by region/account. See:
- https://www.binance.com/pt/support/faq/detail/408ab63b852e47748a9554501669bce5
- https://www.binance.com/pt-BR/support/faq/detail/d5f441e8ab544a5b98241e00efb3a4ab
- https://www.binance.com/en/support/faq/detail/1826c3b426a149949851554bdde227d3

Red Packet is not automatically a guaranteed daily free reward: official documentation also describes it as a way to send crypto gifts that recipients claim with a code, while promotional campaigns are time-limited and eligibility-bound. Verify each current campaign through official sources and in-account eligibility before attempting any claim:
- https://www.binance.com/en/support/faq/detail/6202e6d8dd5b4119801e0e2ecea22790
- https://www.binance.com/en/support/faq/detail/7ccdf38cdd574a5a93be6f053be20f76

No scraper should fabricate codes, bypass access controls, automate abusive repeated claims, circumvent per-user limits, or use multiple accounts to evade campaign terms. Do not submit deposits or trades merely to unlock a reward unless a separately approved, risk-adjusted evaluation supports the action.

## Capital ladder policy

The owner's illustrative ladder is 1 -> 10 -> 100 -> 1,000 units per platform, adding platforms progressively. Treat these as configurable targets, not hard-coded trade instructions or guarantees.

The allocation planner must:
1. Maintain per-account available, locked, pending, and withdrawable balances, plus open positions, fees, and unsettled transfers.
2. Distinguish a target balance from deployable risk capital. Keep explicit reserves and account for minimum order/notional, minimum transfer/withdrawal, network costs, spread, and platform-specific subaccounts.
3. Propose the next platform only after verifying its account eligibility, supported deposit asset/network, fees, operational capability, risk limits, and reconciliation path.
4. Estimate whether a transfer makes economic sense; tiny transfers can be dominated by fixed fees or minimums. Never transfer blindly just to make every account's displayed balance equal.
5. Use a ledger with idempotent transfer intents and states such as PLANNED, APPROVED, SUBMITTED, CONFIRMED, FAILED, and UNKNOWN_OUTCOME. An unknown transfer outcome must trigger reconciliation, not a duplicate transfer.
6. Keep aggregate exposure, correlation, venue/custody risk, and withdrawal access visible. Diversifying venues does not eliminate crypto-market or counterparty risk.
7. Report realized and unrealized PnL separately and deduct costs. Capital progression must be based on reconciled net equity, not just a transient balance or a streak of wins.
8. Support manual approval thresholds and hard risk ceilings. No REAL transfer, native bot activation, copy-trading subscription, reward action with economic obligations, or trade may be executed merely because a target threshold was crossed; existing independent authorization, readiness, preflight, risk, RealModeGuard, operator-authentication and reconciliation gates remain mandatory.

## Implementation sequence

1. Inventory official opportunities and available account/region evidence without acting.
2. Add a typed opportunity schema and evidence/status model with unit tests.
3. Add official-source ingestion with timestamps, expiry handling, duplicate detection, and safe URL/source attribution.
4. Add read-only, account-authorized eligibility and balance checks through supported APIs where possible.
5. Build net-value/risk analysis and a dashboard shortlist; PAPER simulations first.
6. Add per-platform native bot/copy-trading adapters only where official supported interfaces and required permissions are confirmed.
7. Implement capital allocation proposals and transfer reconciliation before any execution adapter. Begin with proposed plans, not automatic transfers.
8. Require explicit operator approval and existing independent gates for every new REAL capability. No profitability guarantee.
