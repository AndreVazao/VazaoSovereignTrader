# Local Validation Handoff — 2026-10-27

## Purpose

Prepare a repeatable Windows-PC validation run for the Sovereign Trader when Desktop Commander is available, or when a human launches an approved Cloud Code Free session on the local checkout. This is a validation-only plan, not permission to change runtime mode or execute financial actions.

## Non-negotiable safety rules

- Keep the engine PAPER/read-only. Do not enable REAL mode, live order placement, cancellation, transfers, withdrawals, or capital routing.
- Do not use, print, copy, or upload exchange API keys, access tokens, cookies, OTPs, private keys, or personal secrets.
- Do not make paid deployments or consume paid resources.
- Do not delete user data, databases, ledgers, recovery snapshots, or logs.
- Do not silently change source files while running the first baseline. Capture the exact Git SHA and working-tree state first.
- If a test hangs, capture the process and logs, stop only the test process that was started, and report the exact command and duration.
- Do not claim a test passed unless its exit code is zero and the output is retained.

## Phase A — inventory and baseline

1. Record the output of git rev-parse HEAD, git status --short, branch name, Python version, and Windows version.
2. Confirm there are no unexpected source changes. Do not reset or clean a dirty working tree.
3. Read docs/TRADING_ENGINE_READINESS_AUDIT_2026-10-19.md and the latest handoff before changing anything.
4. Verify the engine's configured mode and effective REAL guard without starting the engine. Do not reveal environment variables or token values.
5. Create a timestamped evidence folder outside source-controlled runtime data. Store command output and exit codes there.

## Phase B — isolated Python tests

1. Use scripts/run_local_validation.ps1 -Scope python to create/use the isolated .venv and run pytest -q tests.
2. Capture the full output, exit code, start/end time, current SHA, and any timeout.
3. If the full suite fails or stalls, rerun only the named failing test once with verbose output and a bounded timeout. Do not call a stalled suite green.
4. Run focused tests for recovery, reconciliation, order lifecycle, risk/REAL gates, durable learning memory, radar/lead-lag, and hot path. Preserve each result separately.
5. Do not patch code during baseline collection. Send the evidence to the reviewer first; fixes should be made as separate, minimal commits after the failure is understood.

## Phase C — static safety audit

Review current source and tests for:
- All callers of order submit/cancel and capital-transfer/withdrawal adapters.
- Required readiness, preflight, risk, venue-health, authorization, reconciliation, and RealModeGuard checks on every side-effect path.
- Idempotency and ambiguous outcomes after timeout, process crash, partial fill, and restart.
- Fail-closed behavior for stale feeds, malformed book updates, non-finite values, invalid learning records, and corrupt persistence.
- Durable memory ownership/isolation and behavior under multiple writers.
- No path where PAPER signals can be mistaken for fills or execution authorization.
- No credentials or private data in logs/artifacts.

Produce a table with file/line, risk, existing evidence, missing test, and proposed minimal fix. Do not modify source in this phase.

## Phase D — PAPER-only integration checks

Only after Phase B is complete and evidence is captured:
1. Start the diagnostic service only if its documented safe command is available and the effective mode can be verified as PAPER.
2. Verify health/status endpoints and safe shutdown. Do not start live connectors or order adapters.
3. If public market-data collection is tested, use public endpoints only, record exchange/source timestamps separately from local receive/monotonic timing, and verify stale/gap conditions fail closed.
4. Restart only a process started by this validation. Confirm recovery state and that no duplicate side effects are produced.
5. Do not test real account balances, live orders, transfers, or withdrawals.

## Required report

Return:
- Exact SHA, branch, dirty/clean state, OS and Python versions.
- Every command run, exit code, duration, and evidence file path.
- Test totals: passed, failed, skipped, timed out; never omit failures.
- Failures grouped by reproducible defect, environment/dependency issue, or inconclusive/hang.
- Safety audit findings with source locations and a severity rating.
- The smallest recommended next patch and the test that would prove it.
- Explicit statement that no live orders/transfers were submitted and REAL mode was not enabled.

Do not merge, create another branch/PR, or claim production readiness as part of this run.
