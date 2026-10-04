# REAL Execution and Capital Transfer Integration Audit

Date: 2026-10-04 (UTC)
Scope: source-level audit of the current `main` snapshot; no live exchange calls, orders, transfers, credential access, or production changes were performed.

## Executive summary

The repository already contains substantial building blocks for PAPER research, readiness checks, guarded REAL transitions, execution routing, and capital-transfer accounting. These should be integrated and hardened rather than replaced with a second implementation.

This audit is not a certification that REAL trading is safe. The current review found integration boundaries that need explicit tests and/or stricter contracts before any live use.

## Verified existing components

- `PC_ENGINE/core/real_readiness.py`: readiness report includes preflight, sample counts, evidence quality, walk-forward/regime/L2 validation, PAPER reconciliation, watchdog/recovery, pending orders/intents, execution test, credentials, and critical-error checks.
- `PC_ENGINE/core/real_readiness_service.py`: collects evidence and validation reports; its class docstring explicitly says it never authorizes an order.
- `PC_ENGINE/core/real_mode_guard.py`: temporary arm window, explicit phrase, one-time consume, and a process-local human-authorization bit. A new instance starts disarmed (covered by tests).
- `PC_ENGINE/core/execution_gate.py`: fail-closed execution state machine with explicit human authorization, recovery eligibility, and runtime opportunity/risk/exchange/staleness checks.
- `PC_ENGINE/core/risk.py`: final order-risk validation includes finite/positive values, position limits, total/symbol exposure, and per-trade risk cap.
- `PC_ENGINE/core/capital_transfer_execution.py`, `capital_transfer_state.py`, `capital_transfer_reconciliation.py`: transfer intent submission, state transitions, and accounting reconciliation exist.
- API/browser/Android/HUMAN routing abstractions exist in `PC_ENGINE/core/execution_fabric.py`; mobile pairing has a local revocable token registry.
- Dedicated tests exist for the guard, execution gate, risk authorization, transfer execution/state/accounting, reconciliation, and mobile pairing.

## Findings requiring action

### A-01 — Transfer reconciliation treats missing observations as reconciled (high priority)

In `CapitalTransferReconciliationGate.check(None)`, the result currently reports `reconciled=True` while also reporting `enforced=False` and `OBSERVED_DELTAS_NOT_PROVIDED`. `allows_routing(None)` therefore returns true. Any caller that interprets this boolean as a safety gate can accidentally treat the absence of reconciliation evidence as a pass.

Required follow-up:
- Make missing observations fail closed for any decision that gates routing or REAL transfer completion.
- If a non-enforcing informational mode is needed, expose it separately and ensure it cannot be mistaken for an authorization decision.
- Add tests proving missing, malformed, stale, partial, and mismatched observations do not authorize routing.

### A-02 — REAL authorization has multiple state holders (high priority)

`RealModeGuard` stores armed/human-authorized state in memory; `ExecutionGate` separately stores human authorization and execution state. The unit tests confirm the guard is process-local. Separate state holders can drift unless every transition, restart, fail-safe, and recovery path coordinates them.

Required follow-up:
- Document and test one authoritative transition path from PAPER → explicit human authorization → readiness/preflight/reconciliation → REAL_ACTIVE.
- On restart, process uncertainty, stale readiness, or reconciliation failure, default to PAPER/blocked and require fresh evidence.
- Prove the exact confirmation phrase is checked at the user-facing authorization boundary; do not rely on a boolean parameter alone.
- Keep readiness eligible-for-review distinct from authorization to execute.

### A-03 — Transfer bridge needs explicit UNKNOWN_OUTCOME handling (high priority)

The capital transfer state list currently includes PLANNED, APPROVED, SUBMITTED, PENDING, CONFIRMED, FAILED, and CANCELLED, but no explicit UNKNOWN_OUTCOME state. The documented capital-ladder policy requires ambiguous outcomes to be reconciled before retrying.

Required follow-up:
- Add an explicit ambiguous/unknown outcome state and a recovery path that queries authoritative venue/account evidence before any resubmission.
- Verify adapter exceptions and timeouts after submission cannot cause a duplicate transfer.
- Preserve idempotency across process restarts and ensure only verified evidence can transition to CONFIRMED.

### A-04 — Execution routing is intentionally not an authorization boundary

`ExecutionFabric.execute()` verifies owner isolation and adapter availability, while its class documentation says callers must already have passed RiskEngine/RealModeGuard gates. This is a valid separation of responsibilities only if every live adapter entry point is reachable exclusively through a single audited orchestrator.

Required follow-up:
- Trace all callers and live adapter paths; assert that every REAL order requires active execution-gate approval, fresh readiness, risk approval, venue health, and reconciliation.
- Add negative tests for direct adapter invocation and alternate API/browser/Android paths.
- Keep UI automation subject to platform permissions and human security challenges.

### A-05 — Need end-to-end fail-safe/recovery proof

The component tests cover individual gates, but the source-level audit has not yet established that every failure path blocks new entries, reconciles open/pending orders, preserves logs, and resumes only after all gates recover.

Required follow-up:
- Add scenario tests for stale feed, watchdog failure, risk breach, adapter timeout, unknown order result, partial fill, process restart, and reconciliation mismatch.
- Verify safe mode blocks new entries without blindly abandoning open positions or unresolved financial actions.

## Recommended implementation order

1. Fix and test A-01 first because missing evidence must not pass a financial reconciliation gate.
2. Add UNKNOWN_OUTCOME and idempotent transfer recovery tests (A-03).
3. Map every REAL order/transfer call path and centralize authorization checks without weakening any existing gates (A-02/A-04).
4. Add end-to-end fail-safe and restart/recovery tests (A-05).
5. Only after those tests pass, review the integration with the lead/lag evidence pipeline and capital ladder. Keep PAPER as default; do not enable live execution or real transfers as part of this work.

## Scope and limitations

This was a targeted source inspection, not a full local test run or independent security assessment. It did not validate exchange-specific live adapters, account permissions, production cloud identity, Android device enrollment end-to-end, or actual profitability. Existing code and tests are evidence of implemented components, not proof that the complete live system is ready.

## CI status observed during this audit

The GitHub Actions run for commit `620a358391b013282dcae387f1c01057448a378b` (Windows EXE workflow run 37181004491) completed successfully. The `build-exe` and `build-installer` jobs and their smoke tests reported success. This is build/installer evidence only, not a REAL-trading readiness signal.


## Remediation progress on the audit branch

The following changes have now been added to this draft PR; CI is still running and these changes are not yet merged:

- Reconciliation with missing or empty observations now returns `reconciled=false` and `enforced=true`, and routing is denied.
- Added regression tests for missing/empty evidence, a matching accounting result, and accounting mismatch.
- Added `UNKNOWN_OUTCOME` to the capital-transfer state machine.
- The transfer bridge now durably records `SUBMITTED` before calling the external adapter. If the process crashes at that boundary, a later attempt sees a possibly submitted transfer and does not blindly submit again.
- Adapter exceptions become `UNKNOWN_OUTCOME`; retries are blocked for `SUBMITTED`, `PENDING`, `UNKNOWN_OUTCOME`, and `CONFIRMED`.
- Reconciliation must obtain positive venue verification before marking an ambiguous transfer confirmed and applying accounting. A negative/failed verification leaves the result unresolved.
- Added regression tests simulating a timeout at submission, proving the adapter is not called twice, and proving accounting is not applied until venue verification succeeds.

Remaining work: CI results for the latest commit, full caller/path audit for REAL order and transfer routes, and broader fail-safe/restart integration tests. No claim of production readiness is made.


## Follow-up review — execution authorization boundary (2026-10-04)

### New finding and mitigation

A focused review confirmed that `ExecutionFabric.execute()` previously invoked an adapter after checking only owner identity and adapter availability. The docstring delegated authorization to callers, but the fabric did not enforce that an authorization decision had actually been supplied. This left direct or incorrectly wired callers able to cross the adapter boundary.

The audit branch now changes this contract:

- `ExecutionFabric` accepts an explicit per-intent `execution_authorizer` callback.
- Missing callback denies execution with `AUTHORIZATION_REQUIRED`.
- A callback that raises denies execution with `AUTHORIZATION_ERROR`.
- A callback that does not return the literal boolean `True` denies execution.
- Adapter invocation happens only after that check succeeds.
- Tests cover missing authorization and authorization exceptions, asserting the adapter receives zero calls; the positive test injects an explicit approving callback.

This is a fail-closed integration seam, not proof that every production caller supplies a correct policy callback. The callback must bind to the authoritative REAL execution gate and enforce current readiness, risk, venue health, freshness, and reconciliation. The remaining caller/adaptor inventory and end-to-end proof are still required. The capital-transfer bridge also still needs a dedicated review of how its adapter boundary is wired; this change must not be interpreted as completing that separate path audit.

### CI and branch status

The previous commit `1d42053705807d0dc26b32feab3e28268fdcea79` passed the Python suite and Windows EXE/installer builds and smoke tests. New commits that add the execution authorization callback and tests have since been pushed to this branch, so those previous green results do **not** validate the current head. Wait for fresh CI on the latest head before considering merge.

The PR remains draft and unmerged. PAPER remains the default. No live trading, real transfers, production migrations, or paid deployments were performed.


## Latest follow-up note (2026-10-04)

`ExecutionFabric.execute()` now requires an explicit per-intent authorization callback; missing, denying, or throwing callbacks prevent adapter invocation. `CapitalTransferExecutionBridge.submit()` likewise requires a per-request transfer authorization callback in addition to the existing feature flag and legacy authorization boolean. Tests were added to prove missing/raising callbacks do not invoke adapters or mutate transfer state. This is a fail-closed seam only: production wiring to the authoritative REAL gate, risk, readiness, venue health, freshness and reconciliation policy is still unverified. Current head: `b9fb89913bfd1c0e1486fea43f35db39025c4fdc`. Fresh Python and Windows CI are running; prior green results do not validate this head. PR #337 remains draft and unmerged.


## Authorization freshness follow-up (2026-10-04)

A further review found that `SovereignEngine.set_mode("REAL", autonomous=True)` skipped the freshly-consumed authorization check. The autonomous readiness path consumes a one-time authorization before calling `set_mode`, so this skip was unnecessary and exposed a bypass to direct callers able to pass the flag. The check now applies to every REAL transition, including autonomous transitions. A regression test asserts that `autonomous=True` with an merely armed (not consumed) guard is rejected. This closes the specific freshness bypass; it does not certify the complete REAL path or production adapter wiring.

Latest change commit: `03ae6d2916afd5ab45993e30bb88caf9a3d33e5a`; regression-test commit: `99713c5d4878aa9557efb6fa895bd5a4b54f3a8b`. Fresh CI is running for the regression-test commit. Keep PR #337 in draft until the current head's checks finish and the remaining end-to-end/caller audit is complete.


### Compatibility note

The authorization-freshness fix preserves the pre-existing exception message (`REAL mode requires a freshly consumed human authorization`) so existing callers/tests that inspect the message are not needlessly broken. The regression test was aligned with that stable message. Latest branch head after this compatibility adjustment: `44ad8a17283c99efb705047b8a826ea1eab40cce`; fresh CI must validate this exact head.


## Validation update — 2026-10-04

CI for commit `efbad865218f5a77b671221318a25d9eb9d01dd9` completed successfully: Python tests passed; Windows EXE build and smoke test passed; one-click installer build and smoke test passed. These results validate that commit only.

A further regression assertion now explicitly checks that repeated reconciliation of a confirmed transfer leaves exactly one accounting entry per intent. Fresh CI must run for the newer head before this assertion can be called verified. The PR remains draft/unmerged; production caller wiring, safe-mode/restart scenario coverage, and complete execution-path inventory are still outstanding.


## Safe-mode regression coverage (2026-10-04)

Added tests to assert that after a fail-safe transition the execution gate blocks new submissions, a failed recovery check leaves the gate in `SAFEGUARD_PAPER`, and each individual recovery prerequisite (readiness, reconciliation, timing) is mandatory. These are state-machine unit tests; end-to-end engine recovery with real adapter outcomes, pending orders, partial fills, and process restart remains unverified. CI must validate the latest branch head.
