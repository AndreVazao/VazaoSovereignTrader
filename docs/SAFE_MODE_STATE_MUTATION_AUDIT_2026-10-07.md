# SAFE_MODE State-Mutation Audit — 2026-10-07

## Baseline

- Product: `AndreVazao/VazaoSovereignTrader`
- PC: `C:\ProgramasGodMode\VazaoSovereignTrader`
- Audited `main`: `8a20e6ca099d0ec0917e9f38b399e2f24032cd49`
- This is two documentation commits ahead of PR #376 and contains no product-code delta from `953a8bd7db3e26f0d59a01abc41fe6a74a34484a`.

## Scope

The audit covered production Python under `PC_ENGINE`, with explicit searches for:

- `self.state.status` assignments and reads;
- `runtime_status` persistence/restore;
- `SAFE_MODE`;
- dictionary writes to `["status"]` / `["runtime_status"]`;
- generic setters such as `setattr()` / `set_status()`;
- start, pause/resume, stop, mode switching, recovery, autonomous promotion, watchdog/fail-safe and API control paths.

Tests were treated as verification code, not production state-mutating paths.

## Production state writes found

The complete `self.state.status` write inventory in `PC_ENGINE/core/engine.py` is:

1. `_enter_real_fail_safe()` — `SAFE_MODE`.
2. `_enter_real_fail_safe()` — `SAFE_MODE`.
3. `_enter_safe_state()` — `SAFE_MODE`.
4. `start()` — `RUNNING`.
5. `recover_from_safe_mode()` — `OFF`.
6. `pause()` — `PAUSED` or `RUNNING`.
7. `stop()` — `OFF), but only when current status is not `SAFE_MODE`.
8. `_maybe_autonomous_real_promotion()` — `RUNNING`.
9. `cycle()` — `KILL_SWITCH`.

No other production write to the engine runtime status was found.

## Why the non-recovery writes cannot clear SAFE_MODE

### startup / start

`start()` checks `self.state.status == "SAFE_MODE"` before any transition to `RUNNING` and returns without starting workers.

### pause / resume

`pause(False)` rejects the operation while SAFE_MODE is active. The API `/resume` additionally maps that rejection to HTTP 409.

### stop

`stop()` deliberately writes `OFF` only when the current state is not SAFE_MODE. When SAFE_MODE is active it stops workers and persists the latch unchanged.

### autonomous PAPER -> REAL promotion

`_maybe_autonomous_real_promotion()` checks SAFE_MODE before any promotion work and returns immediately. The later `RUNNING` write is therefore unreachable while the latch is active.

### cycle / risk kill switch

The cycle can enter `KILL_SWITCH`, but this is a separate terminal/risk state transition and is not a SAFE_MODE exit. The cycle also has an explicit SAFE_MODE hold before trading work.

### mode switching

`set_mode()` changes PAPER/REAL mode and execution-gate state but does not write `state.status`. Therefore it cannot directly clear SAFE_MODE.

### watchdog / fail-safe / recovery entry

Fail-safe paths call `_enter_safe_state()` or `_enter_real_fail_safe()`, which enter SAFE_MODE; they do not clear it.

### persistence / recovery loader

`runtime_status` in `RecoveryManager` is serialized/deserialized recovery data. It is not an independent runtime-state setter. Startup restores SAFE_MODE through the engine's safe-state entry path.

### API / cockpit

The API control surface delegates to the engine's guarded `start()`, `pause()`, `stop()`, `set_mode()` and explicit `recover_from_safe_mode()` methods. No API route writes `state.status` directly.

## Conclusion

At audited main `8a20e6ca099d0ec0917e9f38b399e2f24032cd49`, the production source inventory supports the invariant:

> **SAFE_MODE can only be cleared by `SovereignEngine.recover_from_safe_mode()`.**

The four previously discovered bypass classes are therefore closed:

1. startup/restart normalization;
2. pause(False)/API resume;
3. autonomous PAPER -> REAL promotion;
4. stop().

No additional production bypass was found in this exhaustive mutation inventory. No artificial PR is required for this audit result.

## Evidence hardening started in the same checkpoint

`recover_from_safe_mode()` no longer accepts caller-supplied boolean claims for readiness, reconciliation or timing.

It now:

- requires explicit recovery confirmation;
- runs fresh preflight itself;
- performs authoritative account reconciliation in REAL;
- collects readiness evidence itself;
- verifies evidence collection freshness;
- verifies market-timing freshness/eligibility;
- persists the actual evidence record used for recovery;
- requires a fresh REAL authorization window when recovering REAL;
- keeps fail-closed behavior on any failed gate.

A dedicated authenticated API endpoint is available at `POST /safe-mode/recover`; it supplies only the explicit human confirmation, never readiness/reconciliation/timing flags.

## Validation

- `py_compile` for changed Python files: passed.
- `git diff --check`: passed.
- Full `test_account_reconciliation.py` remains inconclusive/stalled in the known Windows environment.
- An isolated pytest run also did not terminate after producing its first test result; therefore it is **not** classified as green.
- GitHub Actions were not consumed.

## Next

Continue hardening recovery evidence, then perform the end-to-end REAL caller/path audit. REAL execution remains disabled and no capital operation was performed.
