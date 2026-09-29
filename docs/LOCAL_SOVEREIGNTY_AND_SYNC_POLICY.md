# Local Sovereignty and Background Synchronization

## Non-negotiable rule
Every PC installation is an autonomous local node. The cloud is an optional exchange for approved aggregate learning and recovery metadata; it is not a runtime dependency for the local engine. Network loss must not disable local research, local learning, local history, local PAPER analysis, or safe operation using valid local configuration.

## Online/offline behavior
- Local data, evidence ledgers, model state, history, risk state, and last-known-good configuration remain on the owner's PC.
- If cloud sync is unavailable, keep local operation running and queue/retry synchronization later. Do not clear local state or repeatedly retry in a tight loop.
- If exchange/market-data connectivity is unavailable, do not pretend prices are fresh or execute on stale signals. Offline sovereignty does not mean inventing market data or guaranteeing exchange execution.
- A new installation may work locally in its supported local mode; features requiring cloud identity, remote recovery, or shared artifacts remain unavailable until connectivity returns.
- Mobile control is a local companion when it can reach its paired PC; remote access is optional, not a prerequisite for the PC to run.

## Synchronization policy
- Default cadence: once per 24 hours for pull and push, with bounded request sizes and short network timeouts.
- Synchronization runs as low-priority maintenance, outside the trading hot path. It must not hold trading locks, block market-data ingestion, or delay risk checks/order management.
- Randomized scheduling jitter and exponential backoff should be added by the runtime scheduler before broad deployment; do not run retry loops while offline.
- Push only allow-listed, aggregated technical learning artifacts after validation. Never sync balances, P&L, orders, fills, private trade histories, account identifiers, exchange credentials, tokens, or local ledger rows.
- Pull artifacts as untrusted advice: validate schema, integrity, freshness, expiry, and eligibility before local import. Shared learning never overrides local risk limits, local strategy configuration, or PAPER/REAL gates.
- Configuration updates are a separate signed/versioned/approved protocol. Preserve the last-known-good local version and support rollback; reject unsigned, invalid, expired, or risk-weakening updates.
- Local-only operation remains the default when cloud settings are absent or disabled.

## Implementation status
The local sync helper supports interval-gated pull/push calls with a 24-hour default and the example config sets daily intervals. This is a foundation, not proof that every runtime scheduler already calls these gated methods. Before enabling cloud sync, wire the scheduler to these methods, add jitter/backoff and telemetry, test airplane-mode behavior, and verify no sync work blocks trading cycles. Cloud deployment and onboarding remain separate, unprovisioned steps.


## Background scheduling safeguards

- Cloud synchronization starts on a daemon maintenance thread; engine startup does not wait for a network request.
- Pull and push defaults are 24 hours, independently scheduled and jittered to avoid synchronized traffic across owner nodes.
- Network failures are observable to the worker and use bounded exponential retry delays (60 seconds up to one hour by default), with jitter.
- The worker records only error class names in its in-memory status, not authorization headers, tokens, or response bodies.
- Cloud sync remains advisory and must not block local research, local history, PAPER operation, or local risk controls. Market data and remote exchange actions still require connectivity.
