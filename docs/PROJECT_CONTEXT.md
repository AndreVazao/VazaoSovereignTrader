# CURRENT AUTHORITATIVE HANDOFF — 2026-11-15

**Repository:** `AndreVazao/VazaoSovereignTrader` only.  
**Last verified main:** `d2f0d2f43259b62c96932b8c48dab879dd77cd65` (PR #575 squash merge).  
**Operating rule:** one advancement branch/PR at a time; never write directly to `main`.

## Verified GitHub state

| PR | Scope | Result | Merge commit |
|---|---|---|---|
| [#572](https://github.com/AndreVazao/VazaoSovereignTrader/pull/572) | Public CCXT connector registry/API | Merged | `fb59ef5fedbf3df8b9557d2570810c50340fa1a7` |
| [#573](https://github.com/AndreVazao/VazaoSovereignTrader/pull/573) | One-shot spawned connector worker foundation | Merged | `ed7a4494863fc680f385967a9e99e9df9c17ac67` |
| [#574](https://github.com/AndreVazao/VazaoSovereignTrader/pull/574) | Remove REAL activation controls from PC/Android interfaces; mobile mode PAPER-only | Merged | `9b3afee4b753eed7518e0cb5811f4cca5101f96d` |
| [#575](https://github.com/AndreVazao/VazaoSovereignTrader/pull/575) | Cross-process adaptive leases for backtest/simulation/analysis | Merged | `d2f0d2f43259b62c96932b8c48dab879dd77cd65` |

PR #575 was validated on exact HEAD `9703ddcb4e04cb151b3bd56355ad470cd4700567`:
- Python tests: 1,541 passed, 1 skipped, 96 subtests passed.
- PAPER smoke: passed.
- Windows EXE: build and startup/health smoke passed.
- Windows installer: previous-version install, upgrade, launch, health check, uninstall and Learning Vault SHA-256 preservation all passed in disposable CI.
- Portable Windows artifact was produced (65.9 MB; SHA-256 `24a4d3383e4bd791cfc4aec5c856bb5ca3c6014264caefddfafc35b5c1849dac`). CI artifact is not a formal release and is not physical-PC validation.

Snyk still reports an external integration/quota error. It is not a repository test failure or a vulnerability finding. The available GitHub integration cannot administer the external Snyk installation. Vercel status is not a code test. Android workflows were not applicable to PR #575.

## Active development — [PR #576](https://github.com/AndreVazao/VazaoSovereignTrader/pull/576)

Branch: `feat/connector-worker-os-resource-boundary-2026-11-15`.  
Current HEAD: `26f31c3c854afd1ee35fe793d078612054b45f9e`.  
Base/main: `d2f0d2f43259b62c96932b8c48dab879dd77cd65`.  
PR remains open. GitHub reports `mergeable=true` but `mergeable_state=unstable`.

### Latest fully validated SHA — `22f7275bfda8e586f37aa5245057498c62826a55`

Exact-head workflows completed successfully:
- [Python tests #43750382298](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/43750382298): 1,545 passed, 1 skipped, 96 subtests passed.
- [PAPER smoke #43750382290](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/43750382290): 82 passed.
- [Windows EXE/installer #43750382299](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/43750382299): EXE build/startup/health, DPAPI and worker resource-boundary tests passed; installer previous-version build, silent install, in-place upgrade, launch, health check, silent uninstall and Learning Vault SHA-256 preservation passed.
- Portable Windows artifact: 65,939,831 bytes; SHA-256 `d2505057e1b417c62f021388e72e2958f8df29b972f3d08490d0fa040055c299`; [artifact](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/43750382299/artifacts/14175717825).
- Installer artifact: 233,892,549 bytes; SHA-256 `e75b1108ee88694868748b94b1720e95fdeb0264dac7f3df40bbff01d2d3083b`; [artifact](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/43750382299/artifacts/14176885090).

### Current unvalidated increment — `26f31c3c854afd1ee35fe793d078612054b45f9e`

Two commits after the validated SHA:
- `e610f1654b3d9d39152d37a7f733ec1c5a94bffd`: POSIX worker resource limits now preserve inherited soft and hard ceilings instead of raising an inherited soft limit to the VST-requested value.
- `26f31c3c854afd1ee35fe793d078612054b45f9e`: regression test proves existing POSIX memory/CPU soft limits are never raised.

At the time of this handoff, no Python, PAPER or Windows GitHub Actions runs/checks exist for this current HEAD. Only Vercel preview (not a code test) and CodeRabbit skip are visible. Do not describe the latest fix as CI-validated until new runs are attached to this exact SHA.

The external `security/snyk (andrevazao)` status is `error` due to the exhausted Snyk test quota; this is not a vulnerability finding or repository test failure. Vercel is not a code test. The PR's `mergeable_state=unstable` remains a merge blocker under the operating rules. The GitHub integration cannot administer the external Snyk installation. No merge has been performed.

Filesystem isolation and provider-specific network egress allowlists are still absent. The worker remains disconnected from the live ConnectorRegistry; do not load untrusted third-party code.

## Implemented runtime

### Trading safety and connectors
- VST remains PAPER-only. No LIVE activation, order placement, transfers, withdrawals, exchange credentials or financial account linking.
- PR #574 removed REAL activation controls from PC and Android interfaces; mobile mode selection is restricted to PAPER.
- PR #572 added authenticated read-only connector routes: `GET /connectors` and `POST /connectors/{provider_id}/read`.
- The first adapter uses public CCXT ticker, OHLCV and order-book reads. It reuses existing MarketRadar clients and locks; it does not create duplicate exchange sessions.
- Connector registration is limited to configured venues. A registered adapter is not proof of remote connectivity.
- U-Hodler, private account reads, Android UI automation and Android virtualization are not integrated.

### Connector worker boundary
- PR #573 added `PC_ENGINE/core/isolated_connector_worker.py`: one spawned process per read, strict JSON IPC, request/response size limits, bounded startup/execution wait, sanitized errors and termination on timeout.
- The current development branch adds POSIX `RLIMIT_AS`/`RLIMIT_CPU`, Windows Job Object per-process memory/CPU-time limits with kill-on-close, and removes credential-shaped environment variables before adapter factory execution.
- This worker remains disabled from the live ConnectorRegistry. The new OS-limit implementation is not yet validated by CI on this branch.
- It is still not a complete security sandbox: filesystem isolation and network egress allowlists are absent; the worker otherwise runs under the host user's identity. Do not load untrusted third-party connector code.
- The Windows workflow now explicitly runs the worker boundary tests; Linux/POSIX and Windows exact-head CI must pass before considering the resource boundary validated.

### Adaptive resource admission
- PR #575 adds OS-backed cross-process lock leases for optional backtest, simulation and analysis work.
- Slot selection is serialized; leases are released by the OS if a process exits unexpectedly; lock-store failure defers work.
- This controls only VST entrypoints that use the gate. It does not constrain arbitrary processes or impose CPU/RAM quotas on arbitrary code.
- The shipped adaptive resource setting enables the gate by default. Disabling it bypasses admission control and is not recommended on constrained hardware.

## Operational gaps and readiness

| Area | Current evidence | Remaining work |
|---|---|---|
| Headless backend / Windows | EXE smoke and complete installer lifecycle passed in CI | Physical Windows 10 low-memory PC install/start/health/stop/recovery |
| Adaptive resources | Sampling, budgets and cross-process admission tested in CI | OS quotas for connector workers; sustained low-memory physical test |
| PAPER and risk | PAPER smoke passed; interfaces no longer expose REAL activation | Sustained end-to-end PAPER evidence; preserve all risk gates |
| Market Data / Radar | Public CCXT read-only connector path | Additional providers and end-to-end freshness/provenance evidence |
| Third-party connectors | One-shot worker prototype | OS isolation, quotas, supervision, network/filesystem policy, registry integration |
| Learning Vault | CI upgrade preservation SHA-256 test passed | Operational backup/restore, migration and isolation proof |
| Linux | No validated package lifecycle | Linux packaging, install, start, health, upgrade and uninstall workflows |
| Android | APK/emulator evidence from PR #574 | Physical-device and remote reconnect validation |
| LAN/Tailscale | Architecture and prior code only | Physical reconnect and continuous remote-operation validation |
| Virtual office | Authenticated backend snapshot integration | Physical PC/phone validation; show only backend-confirmed work |
| Release | No formal release recorded | Reproducible signed artifacts and release lifecycle |

## Physical PC blocker — issue #560

[Issue #560](https://github.com/AndreVazao/VazaoSovereignTrader/issues/560) remains open. The target is Windows 10 with approximately 3 GB RAM. Historical measurements reported about 446 MB free during an integrated run and an engine working set around 469 MB; these are not current measurements.

Before any physical-PC intervention:
1. Perform a read-only inventory.
2. Create and verify SHA-256 backups of checkout, configuration, Learning Vault, artifacts and untracked files.
3. Do not terminate processes, overwrite data or change the PC without explicit user authorization.

CI evidence never substitutes for physical validation.

## Next engineering sequence

1. Validate the current worker resource-boundary branch on exact-head Python, PAPER and Windows workflows; inspect Windows Job Object and POSIX resource-limit tests.
2. Keep the worker disabled from the live registry until Windows and Linux enforcement tests pass.
3. Add provider egress policy and filesystem isolation; fail closed where a platform cannot enforce the required controls.
4. Integrate only approved, read-only providers after the isolation contract is proven.
5. Route data through Market Data → Radar → Research with freshness, provenance, source health and confidence.
6. Build and validate Linux packaging.
7. Prepare Android virtualization architecture for multiple providers; do not provision paid services or link accounts without explicit approval.
8. Complete physical PC/Android/Tailscale validation only with explicit user authorization.

## Process and safety rules

- Work only in `AndreVazao/VazaoSovereignTrader`; DGM-MAT and Office Kit are separate projects.
- One active development branch and one advancement PR at a time. Never edit `main` directly; repository branch protection/rulesets were not configured in the last observed state.
- Verify exact PR HEAD and all applicable workflows before merge. Use squash merge with an expected HEAD SHA.
- Snyk and Vercel are external checks; distinguish them from code workflows and report their actual state.
- No physical PC access, private credentials, exchange account linking, LIVE mode or financial operations.
- Do not claim a feature, platform or physical device is validated without direct evidence.
