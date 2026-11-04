# Prompt Master — VST local Windows backend end-to-end validation

**Run this prompt from the primary ChatGPT account** `vazao.andre@gmail.com` with Desktop Commander connected to the old Windows PC that will host VazaoSovereignTrader. The secondary account `aiamorchato@gmail.com` is not the intended account for this validation.

## Mission

Safely validate the **headless Sovereign Trader backend** on the actual target PC, as far as the available build and machine permit. Produce a detailed, evidence-based report that can be returned to the engineering assistant for follow-up fixes.

Do not work on the visual office, Android APK, DGM-MAT, Obscura, or unrelated projects. The backend and persistent learning vault are the priority.

## Non-negotiable safety rules

1. **PAPER/read-only only. Never place a real order, transfer funds, connect with real trading credentials, or switch to REAL/LIVE.**
2. Do not ask for, read aloud, copy, log, or include API keys, passwords, cookies, recovery codes, wallet secrets, or full account tokens. If credentials appear in a screen or file, stop and redact them from evidence.
3. Do not expose the service to the public internet. Preserve loopback-only API binding unless an existing, explicitly approved local configuration requires otherwise. Do not open firewall ports or configure port forwarding.
4. Do not disable antivirus, Windows Defender, SmartScreen, UAC, authentication, or other security controls. If Windows blocks the EXE, capture the exact warning and stop for review; do not bypass it.
5. Do not delete the existing vault, learning database, backups, user data, or old installation. Do not run an uninstall/reinstall test until the current vault has been identified, backed up to a separate safe location, and preservation behavior is understood. The first pass is non-destructive.
6. Do not change the Git branch, merge a PR, push commits, or modify source code as part of the local validation. Record observations and suggested fixes only.
7. Never claim a check passed without command output, screenshot, log, or another reproducible piece of evidence. Distinguish PASS, FAIL, BLOCKED, NOT RUN, and INCONCLUSIVE.
8. Do not print complete environment variables or dump whole configuration files; these can contain secrets. Inspect only allowlisted, non-secret fields.
9. If a step risks data loss, starts a REAL execution path, requires unknown elevated privileges, or could affect live trading, stop that step, record why, and continue with safe independent checks.

## Phase 0 — establish identity and exact build

1. Confirm Desktop Commander is connected to the intended old Windows PC. Record Windows edition/build, architecture, available disk space, current date/time and timezone, and whether the current session is elevated. Do not include the Windows account's full personal path in the report; redact it as `<USER>`.
2. Inspect the repository/PR and identify the exact current PR #522 HEAD at `https://github.com/AndreVazao/VazaoSovereignTrader/pull/522`. Record commit SHA and CI statuses for that exact SHA. Do not reuse CI results from earlier commits.
3. Fetch the PR branch `fix/android-office-layout-2026-10-30` from `origin` and verify the fetched commit SHA matches the PR HEAD before running repository tools. Check `git status` first; never overwrite or reset local changes. If the checkout is dirty or on another task, use a separate clean worktree/clone rather than forcing a checkout. Do not merge PR #522 locally or change the user's active branch.
4. Look for the Windows EXE installer/artifact built for that exact SHA. Verify its origin, artifact name, build workflow result, checksum if supplied, and whether it is a debug/test or production installer.
5. **Do not install a stale, unverified, or mismatched artifact.** If the exact-HEAD Windows build is missing, red, or cannot be authenticated, mark installation tests BLOCKED, save the evidence, and perform only safe read-only machine/repository preflight checks. Do not substitute an old installer without explicitly documenting the mismatch.
6. Record the exact EXE filename, artifact/run identifier, SHA-256, file size, and source URL. Do not run unknown downloaded binaries.

## Phase 1 — pre-install machine and safety preflight

1. Check available disk space and Windows architecture.
2. Check whether a VST installation/service/process already exists. Do not kill processes or overwrite an existing install blindly. Record process/service names, paths, status, and listening ports without dumping command lines that might contain secrets.
3. Search for existing VST data/vault locations without opening or copying secrets:
   - **Current default vault:** `%LOCALAPPDATA%\VazaoSovereignTraderData\vault\` (outside the application install directory).
   - **Legacy vault to discover and preserve in place:** `%LOCALAPPDATA%\VazaoSovereignTrader\vault\` (inside the old install-root layout). If this exists and the current vault does not, mark migration/uninstall as BLOCKED; do not move, copy over, rename, or delete it.
   - Optional override: `VST_VAULT_PATH` (report only whether set and the resolved path; never dump other environment variables). If set, it takes precedence and must be checked for separation from the install directory.
   - Expected layout includes `learning\`, `backups\`, `imports\`, `exports\`, and `logs\`.
4. Record whether the vault and legacy learning SQLite database already exist, their sizes and timestamps, and whether SQLite files have matching WAL/SHM sidecars. Do not delete or alter them.
5. Create a dated local evidence folder outside the install directory and outside the vault, preferably `%USERPROFILE%\Documents\VST-Local-Validation\<timestamp>\`. If a repository checkout is available, also prepare `artifacts/local-validation/<timestamp>/` for sanitized copies. Do not store credentials or raw secret-bearing configs there.
6. If a vault already exists, create a consistent SQLite backup using SQLite's backup mechanism or a documented app-supported backup. If a safe backup cannot be made, do not perform any operation that could replace or migrate the database.

## Phase 2 — install (only after Phase 0 passes)

1. Run the verified installer normally, without elevation unless the installer clearly requires it and the reason is recorded. If UAC requests elevation, pause and ask the owner before approving.
2. Record each installer page, option, install path (redact personal path segments), selected components, and any warning/error. Choose the minimal default install; do not enable REAL trading, external network exposure, autostart with elevated privileges, or optional components that are not necessary.
3. Confirm the install completes. Record installed version/build, EXE path, file version, and SHA-256. If installation fails, stop and collect the exact error and logs; do not repeatedly reinstall.
4. Confirm install/uninstall directories are distinct from the new user vault. If the legacy vault exists inside the install root, do not uninstall or migrate it in this run; continue only non-destructive diagnostics and record the migration as BLOCKED.

## Phase 3 — PAPER-only startup and diagnostics

Before interpreting results, run the repository's read-only Windows audit script from the checked-out PR branch (not from an older copy): `powershell -NoProfile -File scripts/vst_local_backend_audit.ps1`. This script does not start or stop processes, change configuration, or collect credential values. It writes `runtime-audit.md` and `runtime-audit.json` under `%USERPROFILE%\\Documents\\VST-Local-Validation\\<timestamp>\\`. Attach both files to the evidence index. If PowerShell policy blocks it, do not weaken system policy; use an approved invocation method and record the block.

1. Verify configuration using the app's supported command/doctor interface. Confirm configured and effective mode are both PAPER. If mode is missing, ambiguous, REAL/LIVE, or a REAL-execution guard is absent, do not start the trading engine; record FAIL/BLOCKED.
2. Start the headless engine using the documented supported launcher, not by clicking arbitrary internal executables. Record the process PID, start time, and exit code if it exits.
3. Run the supported `vst doctor` / diagnostics command and supported health endpoint. Prefer loopback. Do not expose an API token in command history, output, screenshots, or report.
4. Capture:
   - API liveness separately from engine-running state.
   - Runtime readiness status and reasons.
   - Startup health report path and status.
   - PAPER configured/effective mode.
   - Recovery-integrity checks.
   - Auth state without showing secrets.
   - Worker/service/collector status and heartbeat age, if available.
   - Listening interfaces/ports, verifying no public bind.
   - REAL execution blocking evidence and risk-gate state.
5. A running API alone does not prove the brain is running. A startup status of `STARTUP_CHECKS_PASSED` is not proof of end-to-end readiness. Record each layer separately.

## Phase 4 — lifecycle and persistence test

Run only if Phase 3 is confirmed PAPER/read-only and the supported controls are understood.

1. Start the engine once. Confirm a single expected engine instance and capture health/heartbeat.
2. Exercise a harmless supported read-only diagnostic or synthetic PAPER task. Do not use real market orders, live credentials, fund movement, or non-synthetic external side effects.
3. Write one clearly labelled synthetic learning-memory record using the project's supported test/diagnostic path, if available. Do not fabricate a successful test if no safe supported method exists; mark that subtest NOT RUN and explain.
4. Stop the engine using its documented clean-stop command/API. Confirm the process exits and record logs/exit code.
5. Restart the engine. Verify the synthetic record persists and is readable, recovery integrity passes, no duplicate pending task/execution appears, and no permissions are elevated.
6. Verify API liveness, engine-running state, heartbeat freshness and worker status again.
7. If a stop hangs, a second engine instance appears, recovery fails, or REAL execution becomes possible, stop further lifecycle testing and capture the evidence. Do not force-kill unless explicitly approved after documenting the risk.

## Phase 5 — vault continuity and migration safety (non-destructive first pass)

1. Verify that the active learning SQLite database is located under the user vault, not under the versioned installation directory.
2. Record vault manifest/schema version, directory structure, database file size, and record counts only via safe read-only queries. Do not export private learning content into the report.
3. If a legacy learning DB exists, confirm whether migration/copy was attempted, whether it completed, whether source data remains intact, and whether failure is clearly surfaced. Never delete the legacy source.
4. **Do not uninstall/reinstall in this run unless all of these are true:** a verified vault backup exists outside both install and vault directories; the owner explicitly approves the destructive test; installer behavior is understood; and the test can be done without touching personal data. Otherwise mark uninstall/reinstall persistence as BLOCKED and provide a safe proposed test plan.
5. Do not infer uninstall preservation from path separation alone. The report must distinguish code/config evidence from an actual uninstall/reinstall result.

## Phase 6 — logs, reliability, and security review

1. Collect relevant app/engine/doctor/startup/recovery/installer logs and Windows Event Viewer entries for the test window.
2. Redact API keys, passwords, bearer tokens, cookies, private account IDs, full personal paths, IPs that identify unrelated devices, and unrelated user data. Preserve timestamps, error codes, exception types, relevant stack frames, and sanitized paths.
3. Note startup time, clean shutdown time, restart recovery time, CPU/memory snapshots if readily available, process crashes, warnings, repeated errors, and suspicious duplicate processes.
4. Do not upload raw logs publicly. Include only sanitized evidence in the report; retain raw logs locally for the owner unless explicitly approved for sharing.

## Phase 7 — deliver a detailed report

Create:
- `VST-LOCAL-E2E-REPORT.md` — complete report, using `docs/templates/LOCAL_WINDOWS_BACKEND_E2E_REPORT_TEMPLATE.md` if present.
- `evidence-index.md` — evidence filenames, timestamps, SHA-256 hashes and what each proves.
- Sanitized command output, selected screenshots, and relevant log excerpts.
- Optional machine-readable `results.json` with test ID, status, timestamp, build SHA, evidence references and short finding.

Report must include:
1. Summary and overall result (do not reduce mixed results to a single green check).
2. PC/Windows baseline, installer identity and exact VST commit/build.
3. Test matrix with PASS/FAIL/BLOCKED/NOT RUN/INCONCLUSIVE, expected behavior, actual result and evidence link for every test.
4. Exact startup/doctor/health outputs with secrets redacted.
5. Engine lifecycle timeline with PIDs, heartbeat, stop/restart and recovery evidence.
6. Vault path, schema/manifest, database integrity, migration status and persistence evidence.
7. Network bindings, authentication posture, PAPER/REAL guard evidence.
8. All errors and warnings, ranked by severity, with sanitized stack traces.
9. Reproduction steps and prioritized fixes; distinguish confirmed root causes from hypotheses.
10. Tests not run and why, especially physical uninstall/reinstall and any step blocked by missing build/permissions.
11. SHA-256 hashes for the installer and evidence files.

Save the report and sanitized evidence in the repository if available, under `artifacts/local-validation/<timestamp>/`, and also keep a copy in the local evidence folder. Do not commit or push the report automatically. Tell the owner the exact local path and provide a sanitized copy that can be attached to the engineering chat.

## Stop conditions

Stop the affected test immediately if any of these occur:
- Any REAL/LIVE mode, real credentials, order submission, transfer, or external financial action is detected or requested.
- Installer/build identity cannot be verified.
- A vault or learning database is at risk of deletion/overwrite.
- The app binds publicly or requires opening an external port.
- A security control must be disabled to proceed.
- Data loss, unexplained privilege escalation, or duplicate execution is observed.

When blocked, do not improvise a risky workaround. Record the condition and continue only with independent safe read-only checks.

## Final response from Desktop Commander

Return a concise status plus the full report path. State which tests passed, failed, were blocked, or were not run. Include the exact build SHA and installer SHA-256. Do not claim full end-to-end readiness unless every required lifecycle and safety gate has reproducible evidence.
