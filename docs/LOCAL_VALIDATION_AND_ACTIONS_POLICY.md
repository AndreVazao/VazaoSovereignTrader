# Local Validation & GitHub Actions Policy

Last reviewed: 2026-10-06.

## Objective

Keep routine validation on the owner's PC whenever possible and reserve GitHub Actions minutes for checks that genuinely benefit from a clean hosted environment or release packaging.

## Local-first rule

From the repository root on Windows:

- powershell -ExecutionPolicy Bypass -File .\scripts\run_local_validation.ps1 — Python test suite.
- add -Scope shared-learning for Node tests + build.
- add -Scope windows for the Windows installer build.
- add -Scope all for all locally supported checks.
- Android remains environment-dependent and is not silently attempted on a normal Windows host.

A local pass is development evidence, not a substitute for hosted verification when a release, packaging, environment-specific issue, or security-sensitive change warrants it.

## GitHub Actions policy

Routine PR/push execution is intentionally disabled for the heavy workflows:

- Python tests: manual dispatch only.
- Windows EXE/installer: manual dispatch, plus explicit pc-v* release tags.
- Android APK: manual dispatch, plus explicit mobile-v* release tags.
- Shared Learning: manual dispatch only.
- Artifact pruning remains scheduled monthly because it is maintenance and deliberately lightweight.

This prevents normal commits/merges from consuming the included Actions minute budget.

## When hosted Actions should be used

Use GitHub Actions deliberately when:
1. a clean Ubuntu/Windows environment is materially relevant;
2. EXE/installer or APK packaging needs independent verification;
3. a release tag is being cut;
4. a structural/security-sensitive change needs an independent hosted check;
5. a local environment cannot reproduce the issue.

The current GitHub connector can inspect and modify workflows but does not expose a workflow-dispatch action. Therefore, do not claim that ChatGPT automatically triggered a hosted run unless a future connector or the authorized PC runner actually performs that dispatch.

## Relationship with Desktop Commander

Desktop Commander is the preferred local execution path when the PC is available. It can run the same repository scripts without consuming GitHub Actions minutes. The local runner is explicit and fail-closed: a missing tool or failed command stops validation rather than being treated as a pass.

## Safety boundary

Local validation never authorizes REAL trading, transfers, or bypasses. PAPER/read-only and all existing independent execution gates remain unchanged.
