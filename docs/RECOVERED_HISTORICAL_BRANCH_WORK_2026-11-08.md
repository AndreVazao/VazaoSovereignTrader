# Historical branch recovery audit — 2026-11-08

**Repository:** `AndreVazao/VazaoSovereignTrader`  
**Base reviewed:** `main` at `6b617dc85fd58bf184d2eaff98c8cc4abebec42c`  
**Purpose:** preserve useful historical requirements and record why stale code is or is not being reintroduced. This is an audit, not evidence that every planned capability is implemented.

## 1. Current repository state

- PR #547, `feat: defer optional collector studies under resource pressure`, was merged on 2026-11-07.
- Exact PR head: `30958754ce9394d84500cc3d883b0f7c2bd6c83f`.
- Python tests: PASS; Windows EXE build and smoke: PASS; Windows installer lifecycle: PASS, including previous-version install, upgrade, launch, health check, uninstall and Learning Vault preservation.
- Merge commit / current main at audit start: `6b617dc85fd58bf184d2eaff98c8cc4abebec42c`.
- No open PRs were present at the inventory snapshot.
- The remote branch inventory contained `main` and one old branch: `work/mobile-virtual-office-demo-2026-10-28`. The latter diverges from current main (116 commits ahead, 40 behind). It must not be merged wholesale.

## 2. Recovery decision

Historical branches and closed, unmerged PRs were reviewed by comparing their head commits with current main and checking whether the changed behavior or files already exist in the current implementation.

| Historical PR | Subject | Decision |
|---|---|---|
| #381, #382, #485 | Family roadmap, remote cockpit and adaptive-office requirements | Recover the still-useful requirements into the current documents added with this audit. Old 2026-10-19 infrastructure claims are explicitly treated as stale and must be rechecked. |
| #394 | WebSocket latency inferred from wall-clock subtraction | Already superseded on main. Preserve unknown latency until a validated clock-offset model exists; do not reapply the old patch. |
| #410 | Exploded office mockups and department inventory | SVG/mockup material is already present on main. Keep as visual reference, not runtime evidence. |
| #432 | Binance depth-book state machine | Superseded by a refreshed implementation based on newer main. The state machine and tests are present on main; do not cherry-pick the stale branch. |
| #443, #453, #461, #486 | Integration audits, open-source study and status gates | Main contains later audit/status documents. The old dated snapshots are historical evidence, not authoritative current status. |
| #481 | OKX incremental books synchronizer | The OKX synchronizer and collector integration are present on main. No wholesale branch merge. |
| #488 | Coinbase fail-closed rejection and OKX heartbeat semantics | Current main contains the Coinbase invalidation behavior and the empty equal-sequence OKX heartbeat contract. Keep current implementation. |
| #490, #491, #492, #493 | Approved artwork, Android launcher icon, Windows ICO and CEO wall plaque | Visual/packaging work was not fully carried into current main. Defer rather than import stale binary/packaging changes without current asset provenance and fresh Windows/Android validation. Track as a later visual/branding task. |
| #496, #497 | Synchronized L2 output persistence helper/tests | The current collector has venue-specific output routing and an explicit `synchronized_book_payload` identity boundary. The old helper abstraction is superseded by the current venue+symbol callback. |
| #499, #500 | Android emulator/Maestro smoke and reliability fixes | The Maestro workflow and documentation are present on main; #500 records that this work was carried into the consolidation branch. |
| #505 | Strict public-payload JSON validation | Canonical JSON and provenance implementation are present on main. Do not replay old commits. |
| #506 | Offline mobile virtual-office demo | Current main has a newer and larger office page and retains the offline/adaptive-mode contract test. The old UI file is substantially behind and must not replace the current UI. |
| #519 | Obscura cloud evaluation | The benchmark was not established as valid; keep Obscura optional and outside the critical runtime path until protocol and repeatable measurements are proven. |
| #495, #501 and later merged PRs | Replacement/consolidation work | These merged PRs carry forward important L2, Coinbase/OKX, Android smoke and collector changes. Their merged code is already part of main. |

### Remaining old mobile-office branch

The only old remote branch found was `work/mobile-virtual-office-demo-2026-10-28`. Its 116-commit history includes work that has since been merged or reimplemented on main. The branch's `MOBILE_APP/ui.py` is an older 21 KB version; current main is approximately 47 KB and has a larger office implementation. Both contain the offline demo and adaptive mode concepts. Current main's office page is approximately twice the size of the old version, and the corresponding contract test is already present. Therefore no code from that branch is safe or necessary to import as a whole.

## 3. Requirements recovered into current documents

The following historical requirements remain valid and are now recorded in dedicated documents:

- Headless brain remains authoritative; visual office and mobile cockpit are optional clients.
- Office rendering adapts to hardware and screen size, but must never reduce market-data collection, risk checks, persistence or PAPER integrity.
- The office may show only verified backend state. No fabricated agents, orders, P&L, prices or task activity.
- The mobile office remains an offline visual prototype until it is wired to a versioned, authenticated runtime state contract and tested on a physical phone.
- Remote access must use private authenticated connectivity, owner/device binding, expiring sessions and revocation. Never expose the local API directly to the public Internet.
- Discovery/rendezvous services, if used, are not an execution plane and must not store credentials or private trading state.
- Each user's credentials, balances, positions, orders, strategies, logs and risk settings remain isolated. Only explicitly approved, sanitized, provenance-verified research artifacts may be shared.
- A detected cross-venue price difference is a research hypothesis, not a guaranteed opportunity. Timestamp semantics, feed quality, instrument equivalence, fees, slippage, liquidity and out-of-sample evidence must be checked.
- PAPER/read-only remains the operational boundary. No automatic promotion to REAL, no live orders, and no transfers or withdrawals.

## 4. Current implementation versus remaining work

**Present in current main (code-level evidence):**
- Adaptive resource policy and job gates for research, backtests, PAPER studies and collector-side optional studies.
- L2 venue-specific state/synchronization for Binance, OKX and Coinbase, plus venue-specific persistence outputs.
- SQLite Learning Vault durability, crash recovery, backup manifests and installer preservation.
- Signed/canonical shared-learning provenance and cross-organization identity/provenance code paths.
- Android emulator/Maestro startup workflow and offline virtual-office UI contract.
- Windows EXE and installer lifecycle smoke tests.

**Not certified end-to-end by this audit:**
- Full physical-PC chain from Market Data through Radar, strategy, risk, PAPER and telemetry under sustained operation.
- Physical Android launch/rendering and remote phone-to-PC control.
- Production database-backed shared-learning deployment or live cross-owner enrollment.
- Tailscale pairing/discovery and remote approvals.
- Real-time lead/lag profitability or any strategy's net edge.
- Obscura as a production browser/runtime component.
- Final artwork/icon packaging and visual inspection on physical Windows/Android devices.

## 5. Cleanup policy

1. Keep one active VST development branch and one VST PR at a time.
2. Do not merge a stale branch because it contains many commits. Compare behavior and current code first.
3. Preserve useful requirements in current docs and memory before deleting historical branches.
4. Delete the remaining old mobile-office branch only after this recovery PR is merged and its content is confirmed represented by current main or explicitly deferred here.
5. Do not delete `main`, active release references, tags or evidence artifacts.
6. Snyk quota exhaustion and Vercel preview limits are not code-test failures and must not block relevant engineering validation.

## 6. Next engineering priorities

1. Continue low-memory optimization while preserving continuous public Market Data, Radar heartbeat and durable PAPER persistence.
2. Prove the end-to-end PAPER evidence chain in bounded tests suitable for the old PC.
3. Verify the official PC bootstrap and readiness artifact on the user's machine without running a memory-intensive full suite.
4. Keep remote connectivity and visual-office work behind the backend's stability and physical acceptance gates.
5. Update this audit and the project handoff whenever a material state change is verified.
