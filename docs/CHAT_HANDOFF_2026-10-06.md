# VazaoSovereignTrader — Chat Handoff — 2026-10-06

## Current main baseline

- Repository: `AndreVazao/VazaoSovereignTrader`
- Current main SHA after PR #359 recovery crash-window hardening: `162bdf61a7b19b6e721de9642acce7250e0713ea`
- Latest CI/operations merges: PR #355 CI trigger prune, PR #356 artifact retention prune, PR #357 local-first validation/manual Actions policy, PR #358 handoff refresh, PR #359 recovery crash-window hardening.
- PR #347 merge SHA: `f28a40a7444e9bac1a8997b44171c6ea26d1a5e3`
- PAPER/read-only remains the default. No REAL order, cancellation or transfer authorization was enabled.

## Safety contract

1. Fail closed.
2. PAPER by default.
3. Never infer profitability from stale feeds, gross price differences, advertised rewards or isolated tests.
4. Lead/lag is useful only after timestamps, latency, spread, fees, slippage, liquidity and execution feasibility prove a net executable edge.
5. Unknown order/transfer outcomes require reconciliation; never blindly retry.
6. REAL requires explicit human authorization plus all independent readiness, recovery, preflight, risk, venue-health and execution gates.
7. Browser/desktop/Android automation must respect platform terms and must not bypass MFA, CAPTCHA or anti-bot controls.
8. Do not commit secrets or use paid/cloud resources without explicit authorization.
9. Work normally via dedicated branch -> focused PR -> exact-head CI -> squash merge. Report exact SHA and CI conclusion.

## Verified implementation chain

### Capability/readiness

- PR #338 merged: venue capability contracts and normalized adapter order responses.
- PR #339 merged: concrete venue capability verification; static method presence is not REAL authorization.
- PR #340 merged: runtime read-only probes for historical/realtime market data, balances and positions; write/transfer probes are blocked.
- PR #341 merged: append-only persisted capability evidence.
- PR #342 merged: only fresh, positive, environment-matched persisted evidence can promote an already-declared capability.
- PR #343 merged: REAL readiness consumes fresh persisted evidence and fails closed when evidence storage is unavailable/stale/negative.
- REAL order submit/cancel and capital transfer remain unverified/critical unless separately proven and explicitly authorized.

### Capital transfer

- PR #344 merged: fail-closed transfer contract with PREPARED/SUBMITTED/CONFIRMED/UNKNOWN_OUTCOME/BLOCKED.
- PR #345 merged: durable capital-transfer journal/reconciliation.
- PR #346 hardened journal integrity and idempotency collisions; corrupt/unreadable/invalid-schema journals fail closed and reused idempotency keys with different intent are BLOCKED.
- UNKNOWN_OUTCOME is never blindly retryable.

### Recovery and exactly-once

- PR #347 merged: ledger idempotency is protected by a persistent OS-level lock; scan+append is serialized across processes and ledger append is fsynced before success is returned.
- PR #348 merged: `RecoveryManager` durability hardening.
  - `save_positions()` now routes both primary and backup snapshots through `_write_json_atomic()`.
  - Temporary files are fsynced before replacement.
  - Parent directories are fsynced where supported.
  - `clear_reconciliation()` fsyncs the parent directory after journal unlink.
  - Windows remains supported through best-effort directory fsync because directory handles may not support fsync there.
- PR #348 exact-head CI:
  - Python #2949 SUCCESS
  - Windows EXE #730 SUCCESS, including EXE and installer smoke paths.
- PR #348 merge SHA: `0979c5242a944a63a34a258fe323b14c77b6ec2e`.

## Important recovery semantics

- `PC_ENGINE/core/recovery.py` uses schema version 2 with integrity SHA-256.
- Recovery has primary + backup snapshots.
- Reconciliation journal is durable before state mutation and integrity-checked before commit.
- Primary/backup writes use atomic replacement with file fsync and best-effort directory fsync.
- Corrupt primary can fall back to a valid backup.
- Ambiguous financial outcomes must remain pending/unknown until authoritative reconciliation.
- The next recovery audit should focus on any remaining multi-writer assumptions, crash windows around commit/clear ordering, and end-to-end restart/reconciliation tests rather than merely adding more unit tests.

## Recovery audit checkpoint ? PR #359 merged 2026-10-06

- Identified and fixed a crash window in PC_ENGINE/core/recovery.py: if the process crashed after the primary snapshot was atomically written but before the backup snapshot was written, the durable reconciliation journal could previously be cleared while the backup still pointed to an older generation.
- PR #359 closes this window by reading/verifying the backup on every reconciliation commit and repairing a missing, invalid or stale backup before the journal can be cleared.
- Added regression coverage simulating a crash immediately after the primary write and verifying restart recovery leaves primary and backup at the same integrity digest.
- PR #359 squash-merged as 162bdf61a7b19b6e721de9642acce7250e0713ea.
- Local targeted recovery/durability validation: **10 passed**.
- Hosted exact-head Python suite run 37503646116 on e4c0b5f8e27b3dafa91a96560a2d05ea50637d3a: **SUCCESS**.
- This hardening remains PAPER/read-only; no REAL order, cancellation or transfer authorization was changed.
- Next recovery focus remains the broader restart/reconciliation audit: primary/backup crash permutations, UNKNOWN order outcomes, partial fills, reconciliation mismatches and SAFE_MODE behavior.

## GitHub Actions / local validation

- Routine heavy Actions are now manual/release-only to conserve the exhausted included minute budget.
- Python and Shared Learning workflows are manual dispatch only.
- Windows EXE/installer and Android APK are manual plus explicit release tags.
- Artifact pruning remains monthly and intentionally lightweight.
- Desktop Commander is the preferred local validation path.
- Added scripts/run_local_validation.ps1 with isolated .venv support for Python tests and optional shared-learning/windows scopes.
- The GitHub connector currently does not expose workflow dispatch; never claim a hosted run was triggered unless an actual dispatch-capable path performs it.
- A PC validation attempt initially failed because the active global Python lacked ccxt; the local runner was then hardened to isolate dependencies in .venv. Full dependency installation was still underway when the temporary validation process was stopped. No application-code failure was established.

## Current strategic next steps

1. Complete the REAL caller/path audit from human authorization through readiness freshness, preflight, reconciliation, risk, venue health, execution gate, adapter, persistence and recovery.
2. Strengthen end-to-end recovery tests for stale feed, watchdog, risk breach, adapter timeout, unknown order result, partial fill, restart and reconciliation mismatch.
3. Audit browser and Android execution boundaries; keep observation separate from execution.
4. Complete adapter contract coverage for normalized symbol, side, amount, client order ID, status, filled quantity, fee denomination and venue identity.
5. Recheck readiness evidence freshness and capability verification across every REAL caller.
6. Only after the safety chain is clean, return to PAPER research priorities:
   - AMD contextual feature: accumulation/manipulation/distribution/absorption as contextual evidence only.
   - lead/lag via source timestamps and WebSockets.
   - isolated Vibe-Trading research sandbox with no keys and no executor path.
   - optional prediction-market observer only if a concrete, measurable edge exists.
7. No automatic REAL promotion.

## Repository documents

- `docs/MASTER_ROADMAP_AND_AGREEMENTS.md` — master product/safety/roadmap charter.
- `docs/PROJECT_CONTEXT.md` — live engineering history and continuity context.
- `docs/REAL_CAPITAL_EXECUTION_AUDIT_2026-10-04.md` — REAL capital execution audit.
- `docs/OPPORTUNITY_DISCOVERY_AND_CAPITAL_LADDER.md` — opportunity/capital design.
- `docs/OPPORTUNITY_REGISTRY.md` — typed opportunity evidence/state model.
- `docs/CHAT_HANDOFF_2026-10-05.md` — previous handoff; this file supersedes it for the current session.

## Working style

The owner prefers autonomous forward progress with focused small-to-medium PRs rather than micro-PRs or giant changes. When the owner says “Avança”, inspect live GitHub state, implement the next safe coherent increment, run/verify CI, merge when green, document the result and continue to the next hardening item.

## Do not lose these boundaries

- No guaranteed profits.
- No real trading because a strategy looks promising.
- No transfer because a capital threshold was reached.
- No browser/Android automation that bypasses security controls.
- No REAL authorization inferred from capability declarations, persisted evidence, reports or CI.
- No claim that CI is green unless the exact head SHA has SUCCESS conclusions.

## Recovery audit checkpoint � PR #364
- PR #364 merged: focused crash-window regression coverage for reconciliation ledger side effects.
- Local targeted validation: tests/test_recovery_pending_orders.py � **10 passed**.
- Covered: ledger write interruption after durable state commit; restart with journal still pending; successful retry without duplicate ledger record; journal-clear interruption after successful ledger write; restart idempotency.
- No production runtime code changed in #364.
- Main merge SHA: ce82f1b885dbd997dd082ee7fb8bcfe051f558e6.
- Next recovery focus remains authoritative reconciliation mismatch / SAFE_MODE transitions and any remaining primary/backup crash permutations.


## Recovery audit checkpoint — authoritative mismatch / SAFE_MODE
- Reviewed `SovereignEngine.reconcile_account_state()`: authoritative venue balance/open-order reads are the source of truth; local state is never overwritten to hide a mismatch. Position, base-flow, quote and unexpected-asset mismatches return BLOCKED and enter SAFE_MODE.
- Existing regression coverage already asserts position mismatch -> BLOCKED + SAFE_MODE (`tests/test_account_reconcilition.py`) and real-start reconciliation blocks failed account reconciliation.
- Local Windows pytest execution for this reconciliation module currently stalls after starting the test process even on the existing baseline test; it was terminated to avoid hanging the PC. This is recorded as **inconclusive local execution**, not green. No runtime code changed in this checkpoint.
- No hosted Actions run was triggered because this is audit/documentation-only and the current Actions budget policy remains local-first.
- Next recovery focus: remaining primary/backup crash permutations and restart/idempotency around authoritative reconciliation evidence, with no automatic state correction on mismatch.


## Recovery audit checkpoint — PR #367 — automatic engine restart ledger replay

- PR #367 merged to main as 25c808e31103e5f5e0468205cd959001338884ad.
- Added focused integration coverage in tests/test_engine_restart_recovery.py for the real startup recovery path: a durable reconciliation journal containing a ledger record is discovered by a fresh SovereignEngine, the target state is committed, the ledger side effect is replayed idempotently, the journal is cleared, and a second restart does not duplicate the trade.
- Local targeted validation on PC-Vazao-Anjos: 4 passed (tests/test_engine_restart_recovery.py).
- This checkpoint changed tests only; no production runtime code, REAL authorization, order path or capital-transfer path changed.
- The test closes an end-to-end gap between the lower-level crash/replay tests and the actual engine startup recovery path.
- Local PC and GitHub were synchronized before the change and will be synchronized back to main after this documentation checkpoint.
- Next recovery audit: exercise the remaining primary/backup crash permutations and authoritative account-reconciliation mismatch/restart behavior without introducing automatic state correction.

## Current live baseline (supersedes older SHA references above)

- main: 25c808e31103e5f5e0468205cd959001338884ad
- PRs #355 through #367 relevant to the current recovery/local-first line are merged as documented across this handoff.
- Routine hosted Actions remain constrained by the exhausted included-minute budget; final Windows installer/EXE and Android APK builds remain GitHub Actions responsibilities and are not replaced by local builds.
- PAPER/read-only remains the default. No REAL order, cancellation or capital-transfer authorization is enabled.
