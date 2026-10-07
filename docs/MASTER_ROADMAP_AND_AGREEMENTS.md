# Vazao Sovereign Trader — Master Roadmap, Agreements & Continuity Guide

Last reviewed: 2026-10-06 (UTC)
Repository: https://github.com/AndreVazao/VazaoSovereignTrader
Purpose: durable project charter and restart point for future conversations. This document consolidates the owner's stated goals, agreed product behavior, architecture constraints, implementation order, safety requirements, and open work. It complements `docs/PROJECT_CONTEXT.md` (the live engineering handover) and `docs/OPPORTUNITY_DISCOVERY_AND_CAPITAL_LADDER.md` (opportunity/capital design).

## 1. North-star objective

Build a dependable, installable, user-controlled trading research and execution system that can:
- run on the owner's PC (Windows first, with cross-platform awareness) and accumulate market data continuously;
- operate PAPER by default, generate reproducible research, and measure outcomes after realistic costs;
- discover and inspect authorized trading venues, websites, desktop applications and Android apps;
- determine, with evidence, which features are accessible, unsupported, blocked, unknown, or require human action;
- identify legitimate exchange-native automation, copy-trading, fee-reduction, research, reward and promotion opportunities;
- eventually propose and, only after explicit authorization and all existing independent gates, perform permitted actions;
- provide a clear desktop/mobile-friendly dashboard for operations, evidence, venue status, blockers and next steps;
- allocate capital progressively across authorized accounts using a configurable ladder, while respecting costs, reserves, exposure and reconciliation.

This is a long-term engineering objective, not a claim that all capabilities are already implemented. The status of each capability must be supported by code, tests and current evidence.

## 2. Non-negotiable operating principles

1. **PAPER-first:** no live orders, transfers, bot activation, copy-trading subscriptions or financially binding reward actions by default.
2. **Human authorization:** reaching a target, finding an opportunity, or passing a study never grants REAL authorization by itself.
3. **Fail closed:** preserve Readiness, preflight, reconciliation, Risk Engine, RealModeGuard, operator authentication/approval and other existing gates. Never bypass or weaken them to make a feature work.
4. **No profitability promises:** operational health, model quality, statistical evidence, economic value and permission to execute are separate dimensions.
5. **Evidence over assumptions:** unknown is a valid state. A visible button does not prove account eligibility; a healthy feed does not prove a profitable venue; a report file does not prove sufficient evidence.
6. **Official and permitted access:** prefer documented official APIs with least-privilege scopes. Browser/desktop/mobile automation must comply with platform terms and access controls.
7. **Human handling of security challenges:** never bypass MFA, CAPTCHA, anti-bot controls, device approval, or account permission grants. Ask the owner to complete the required step.
8. **No credential harvesting:** never commit, print or expose secrets, API keys, tokens, passwords, recovery codes, session cookies or private account data. Do not store credentials in the browser reconnaissance layer.
9. **No abusive rewards behavior:** no fabricated codes, repeated abusive claims, multi-account limit evasion or campaign-term circumvention.
10. **No unapproved spend/deployment:** do not provision cloud resources, deploy services, enable paid data or incur costs without current cost/terms review and explicit owner authorization.
11. **Idempotency and reconciliation:** after an ambiguous order/transfer result, reconcile before retrying. Never duplicate a possibly successful financial action.
12. **Repository discipline:** read the current project context and inspect live GitHub state before acting; work on a dedicated branch and PR; never commit normal feature work directly to main.
13. **Honest reporting:** report exact SHA, PR, tests and CI status. Do not say a check passed if it is pending, missing, or run against a different commit.

## 3. Execution and evidence states

Keep these dimensions independent in the code and dashboard:

### Operational state
- Is the process alive?
- Is the venue connection recent?
- Are timestamps, symbols and market data valid?
- Are there gaps, reconnects, stale feeds, rate-limit errors or storage problems?

### Research/economic state
- Are there enough observations?
- Are calibration, chronological out-of-sample, walk-forward, regime and stressed-cost tests complete?
- Are results net of fees, spread, slippage, funding/borrow and other relevant costs?
- Are confidence intervals, sample size, drawdown, tail risk and uncertainty visible?
- Are findings stable outside the training period and across regimes?

### Capability and account evidence
- Is the platform/feature officially supported?
- Is account and region eligibility known?
- Are permissions sufficient and least-privilege?
- Are markets, order types, minimums, limits, fees and reconciliation semantics understood?
- Is the capability confirmed, unknown, blocked, unsupported or awaiting human action?

### Authorization state
- Is the system PAPER or REAL?
- Have all independent readiness, risk, preflight, reconciliation and operator approval gates passed?
- Is the requested action explicitly authorized for this specific scope?
- Has the action outcome been confirmed by authoritative platform evidence?

These states must never be collapsed into one green light. A GREEN venue health indicator is operational only, not a recommendation to trade.

## 4. Platform reconnaissance and audit requirements

The owner's goal is for the trader to understand where it can operate and what it can safely do across:
- browser-based trading platforms;
- desktop applications on Windows and, where feasible, other operating systems;
- Android applications/APKs, through an authorized device bridge or a controlled emulator/device environment.

For every venue/platform, create an evidence-backed capability inventory covering, where available:
- platform identity, official URLs/app identity, jurisdiction/region limitations and supported connection method;
- connectivity, current-page/app structure and navigation areas that are safely inspectable;
- account eligibility, KYC status only where the owner-authorized interface exposes it, and permission scopes;
- balances by asset and account compartment, locked/pending/withdrawable funds, open positions and liabilities;
- supported markets, market status, order types, tick/lot/notional minimums, rate limits and trading hours where applicable;
- maker/taker fees, spreads, funding/borrow costs, withdrawal/network fees and transfer minimums;
- native bots, copy trading, promotions, rewards, rebates, research tools and their current eligibility/expiry;
- official API/UI automation options, permission requirements, failure modes and safe stop/cancel semantics;
- order/transfer status retrieval, reconciliation support, idempotency keys or safe duplicate prevention;
- last successful observation time, source, confidence, gaps, and blockers requiring owner action.

Use explicit states such as `CONFIRMED`, `UNKNOWN`, `BLOCKED`, `NOT_SUPPORTED`, `EXPIRED`, `NEEDS_HUMAN_ACTION`. Include the evidence source and timestamp. Never infer balances, assets, permissions or account eligibility from public pages or labels alone.

### Current limitations to preserve
- The browser adapter's current-page structural inventory is read-only and bounded; it is not a full-site crawler or a complete account audit.
- It must not click, navigate, submit forms, read input values, cookies, browser storage, credentials, balances or positions unless a separately reviewed, explicitly authorized capability is implemented with appropriate tests.
- The Android ADB bridge currently must not be described as capable of launching arbitrary APKs or submitting trades unless code and tests prove that capability. Treat device/emulator interaction as a separate capability track.
- Do not claim that a venue has been fully audited until each applicable inventory field has evidence or a recorded blocker/unknown state.

## 5. Opportunity discovery

Discover legitimate opportunities from official, current sources and owner-authorized account surfaces:
- native exchange automation (for example spot grid, DCA, rebalancing, where offered);
- copy trading and strategy marketplaces;
- official rewards, campaigns, vouchers, red packets and fee rebates;
- fee tiers, maker/taker discounts, supported research endpoints and data tools;
- public market data and potential cross-venue latency/lead-lag observations;
- the project's own PAPER-tested strategies.

For each candidate store venue/account scope, discovery time, official source URL, source capture time, campaign start/end/expiry, eligibility conditions, costs, restrictions, required permissions, risks, automation method, test state and rationale.

Opportunity states should distinguish at least:
`DISCOVERED`, `ELIGIBILITY_UNKNOWN`, `ELIGIBLE_CONFIRMED`, `NET_VALUE_POSITIVE_ESTIMATE`, `PAPER_TESTED`, `READY_FOR_EXPLICIT_APPROVAL`, `CLAIMED_OR_ENABLED_CONFIRMED`, `EXPIRED`, `BLOCKED`, `UNSUPPORTED`, `REJECTED_BY_POLICY`, `UNKNOWN_OUTCOME`.

An estimated positive net value is not a guarantee. Account for trading fees, spread, slippage, funding/borrow, transfers, network costs, lockups, liquidity, concentration, downside, platform/custody risk and relevant tax/accounting considerations where estimable. Mark missing inputs as unknown. Never use advertised APY, win rate, leaderboard placement, gross rewards or social-media claims as standalone proof of profitability.

For Binance or any other exchange, use current official documentation and verify region/account availability. A historic campaign must be marked expired, not advertised as currently claimable. Do not assume daily free rewards exist.

## 6. Capital ladder and portfolio administration

The owner's illustrative ladder is 1 → 10 → 100 → 1,000 units per platform/account, progressively bringing additional platforms into the plan. The currency and targets must be configurable; the example is not a hard-coded trading rule.

Required behavior:
1. Track reconciled net equity separately from available, locked, pending, withdrawable and unsettled balances; include open positions, liabilities and costs.
2. Separate target balance from deployable risk capital; preserve reserves and aggregate risk ceilings.
3. Before proposing a new platform, verify eligibility, asset/network compatibility, deposit/withdrawal limits, fees, account compartment, operational support and reconciliation path.
4. Estimate whether a transfer is economically sensible; small transfers may be dominated by fixed fees/minimums. Do not blindly equalize displayed balances.
5. Account for correlated exposures and venue/custody/withdrawal risk; adding venues does not eliminate market risk.
6. Use an auditable transfer-intent ledger with states such as `PLANNED`, `APPROVED`, `SUBMITTED`, `CONFIRMED`, `FAILED`, `UNKNOWN_OUTCOME`. An unknown outcome requires reconciliation, not a duplicate transfer.
7. Show realized and unrealized P&L separately, net of costs. Capital progression uses reconciled net equity, not a transient balance or a short winning streak.
8. Make allocation proposals visible before action, with source balances, destination, amount, fees, expected post-transfer balances and risk impact.
9. Never initiate a real transfer or trading action solely because a threshold was crossed. Explicit owner approval and all existing independent gates remain mandatory.
10. Never promise that each account will reach a target or that a ladder will produce a profit.

## 7. Research, PAPER and REAL promotion

PAPER research should grow only as valid data/outcomes arrive. Reports must make sample size and data coverage explicit. Required evidence includes, as applicable:
- data freshness and timestamp validation;
- calibration and outcome quality;
- chronological out-of-sample evaluation;
- walk-forward evaluation;
- regime-specific evaluation;
- cost stress (fees, spread, slippage, funding/borrow as relevant);
- bootstrap/uncertainty analysis, drawdown and tail-risk metrics;
- realistic execution and reconciliation behavior;
- sufficient history and stability to justify further review.

Missing evidence is `MISSING`, not a pass and not proof the strategy fails. PAPER evidence may inform a human review but must never self-authorize REAL. Do not optimize thresholds on the final test set or present in-sample results as out-of-sample evidence.

Before any REAL capability, preserve all existing independent gates and require explicit approval scoped to the particular action/capability. No hidden auto-start of trading, no silent mode switch, no REAL promotion from a scorecard or report, and no action based on opportunity discovery alone.

## 8. Dashboard and operator experience

The dashboard should be readable on desktop and phone, and clearly separate:
- engine mode/state (PAPER by default; REAL LOCKED until all gates pass);
- market-data collector health, last event, age, reconnects, gaps and storage health;
- venue/platform list sourced from configured and observed platforms, not an invented fixed list;
- GREEN/YELLOW/RED operational health with visible definitions and last-seen evidence;
- independent economic/research evidence, sample sizes, OOS/walk-forward/regime coverage and stressed costs;
- platform capability audit with confirmed/unknown/blocked/unsupported states;
- opportunity shortlist with official source, expiry, eligibility, estimated net value, risks and required human action;
- capital ladder plan, reconciled balances and proposed transfers (no silent execution);
- clear alerts, blockers, next actions, audit history and deterministic exports.

RED means review, not automatic deletion. Operational health is not economic performance. A missing report is not a negative strategy verdict. P&L must only be shown when backed by actual ledger records and should distinguish realized/unrealized and gross/net values.

## 9. Browser, desktop, Android and human-in-the-loop automation

- Prefer official APIs for supported actions and read-only APIs for audit where possible.
- Use UI automation only when permitted and necessary; document scope and known limitations.
- Do not evade MFA, CAPTCHA, anti-bot or rate limits; do not automate prohibited access.
- Never store credentials in reconnaissance artifacts or log private account details.
- Require human confirmation for permission grants, security prompts, unfamiliar account actions and any real-money obligation.
- Keep observation/read-only adapters separate from execution adapters.
- Execution adapters need explicit capability declarations, input validation, preflight, risk checks, idempotency, timeout/unknown-outcome handling, reconciliation and tests for rejected/cancelled/partial/filled outcomes.
- Never treat REJECTED or CANCELLED as successful. Avoid retrying an order when the prior submission may have succeeded.
- If a platform does not support safe automation, mark it unsupported or human-assisted rather than inventing capability.

## 10. Security, privacy, recovery and operations

- Keep API keys least-privileged; trading permission only when specifically required and authorized; withdrawal permission should not be enabled for trading adapters by default.
- Never commit secrets. Use local secret handling documented for the target OS, redact logs and keep test fixtures synthetic.
- Keep cloud sync/deployment disabled unless explicitly authorized after cost, security and terms review.
- Maintain health checks, reconnect behavior, bounded queues, disk growth warnings, safe shutdown/restart and deterministic diagnostics.
- Make local persistence and recovery behavior documented; avoid duplicate actions after restart.
- Audit logs should capture action intent, approval identity/context, timestamps, request IDs where safe, authoritative outcome and reconciliation result without secrets.
- Data retention, backups and recovery steps should be explicit; do not claim a backup exists unless verified.
- The PC node should be installable and verifiable before it is treated as an always-on operational node. Never imply a process is running merely because installation code exists.

## 11. Repository workflow and continuity protocol

At the start of every new conversation:
1. Read `docs/PROJECT_CONTEXT.md` on current `main`.
2. Read this master roadmap and any relevant subsystem design document.
3. Query live GitHub for current main SHA, open PRs, branches and CI; do not assume this file's snapshot is current.
4. Inspect active PR diffs and check exact-head status before making changes.
5. Keep one active implementation PR where practical. Use a dedicated branch for each coherent change.
6. Update tests and docs with code. Inspect the complete diff, check for secrets, unsafe defaults, scope creep and untested behavior.
7. Merge only when the PR is mergeable, there are no blocking defects/conflicts, and all required checks are green on the exact head SHA.
8. After merge, verify resulting main SHA and post-merge workflows. If post-merge runs are pending, record them as pending.
9. Update `docs/PROJECT_CONTEXT.md` with actual work, branch/PR/SHA, test/CI status, unresolved blockers and next action. Update this roadmap when product agreements or scope change.
10. End each session with a useful handoff: completed, not completed, current exact GitHub state, risks/blockers, next recommended engineering step, and a copy/paste continuation prompt if the conversation is getting long.

Never invent test results, workflow IDs, commit SHAs, account facts or platform capabilities.

## 12. Current verified baseline at this document's creation

- PR #313 browser terminal outcome semantics fix was merged as `fd34043a974d93f1549751e9668da3d9a808bb6a`.
- PR #314 read-only browser reconnaissance inventory was merged as `2261776ddaf989bb4b62b71c8362a9d16e0c8e44`.
- PR #315 opportunity discovery and capital ladder documentation was merged as `753b6f7a6b0eac3f1e1aa0b8a1e583429321cdad`.
- Main was verified at `753b6f7a6b0eac3f1e1aa0b8a1e583429321cdad` when this roadmap branch was created.
- PR #315 exact-head Python workflow run 37012132630 reported SUCCESS. No PR-triggered post-merge workflow run was returned for the merge SHA at the time of the check; this is not proof that all post-merge workflows passed. Verify current status before claiming it.
- PR #314 post-merge workflow status was pending at the prior handoff; recheck it against the then-current main SHA.
- The current browser reconnaissance adapter is read-only, current-page structural inspection, not a full platform/account audit.
- No verified REAL promotion is recorded. Preserve PAPER default and all independent authorization gates.
- No cloud provisioning, paid service activation or deployment is authorized by this roadmap.

## 12A. Recovery/exactly-once hardening checkpoint — 2026-10-06

- PR #347 merged: ledger idempotency is serialized across processes with a persistent OS-level lock and fsync before returning success. Merge SHA: `f28a40a7444e9bac1a8997b44171c6ea26d1a5e3`. Python #2942 and Windows EXE #727 were SUCCESS on the exact PR head.
- PR #348 merged: recovery snapshot durability was hardened. `save_positions()` now uses the durable atomic writer for both primary and backup snapshots; the temporary file is fsynced before replacement; directory-entry changes are fsynced where supported; reconciliation-journal removal also fsyncs its parent directory. Merge SHA: `0979c5242a944a63a34a258fe323b14c77b6ec2e`.
- PR #348 exact-head CI: Python #2949 SUCCESS; Windows EXE #730 SUCCESS, including EXE and installer smoke paths.
- Capital-transfer hardening from PRs #344/#345/#346 remains active: explicit transfer authorization, durable journal/reconciliation, UNKNOWN_OUTCOME fail-closed handling, journal integrity errors fail closed, and idempotency-key collision blocking.
- No REAL order, cancellation or capital-transfer authorization was added by these increments. PAPER/read-only remains the operating default.

## 13. Implementation backlog (sequenced)

### Track A — CI and repository continuity
- [ ] Recheck PR #314 post-merge workflows and PR #315 resulting-main workflows against current main SHA.
- [ ] Keep this master roadmap and `PROJECT_CONTEXT.md` synchronized on actual status.
- [ ] Inspect open PRs/branches and avoid parallel conflicting implementation work.

### Track B — opportunity schema and tests (next implementation)
- [x] Define typed opportunity record and enum/state transitions (initial implementation on branch `feat/opportunity-registry-schema`).
- [x] Validate HTTPS source URL, source-capture/discovery timestamps, and expiry constraints.
- [x] Define eligibility evidence, cost estimates, risk notes, required permissions and no-action safety invariants.
- [x] Add append-only JSONL registry with latest-state snapshots, malformed-line tolerance and idempotent identical writes.
- [x] Add unit tests for invalid transitions, expired records, missing provenance/eligibility evidence and no-action defaults.
- [x] Ensure this module cannot authorize execution; official-source allowlisting, automated expiry sweeps and ingestion remain open.

### Track C — official-source ingestion and evidence
- [x] Define the initial exact-host allowlist policy boundary and safe URL attribution (metadata-only; no network fetch yet; `PC_ENGINE/opportunity/source_policy.py`).
- [ ] Implement separately reviewed read-only fetch/cache adapters for public official information with timestamps and source hashes where appropriate.
- [ ] Treat source text as untrusted data, never executable instructions.
- [ ] Track source changes and campaign expiry; mark unavailable/stale sources as unknown.
- [ ] Do not scrape private account pages without explicit scope and approved access.

### Track D — account/platform capability audit
- [ ] Extend the read-only platform inventory schema before adding UI behavior.
- [ ] Add official API capability probes with least-privilege permissions.
- [ ] Capture account/region eligibility only from authorized authoritative evidence.
- [ ] Inventory balances/assets/positions/permissions/markets/order types/fees/limits only where explicitly authorized and securely handled.
- [ ] Document browser, desktop and Android capabilities separately; do not overstate the current ADB bridge.
- [ ] Add actionable blockers and human-assisted flows for MFA/CAPTCHA/permission approval.

### Track E — net value and risk evaluation
- [ ] Build reusable cost accounting for fees, spread, slippage, funding/borrow, transfer/network fees and lockup.
- [ ] Separate gross claim/return from estimated net value and realized net outcomes.
- [ ] Represent uncertainty and missing inputs; avoid false precision.
- [ ] Add PAPER comparisons for native bots/copy trading/strategy ideas where data permits.
- [ ] Include drawdown, concentration, liquidity and venue/custody risk; no recommendation based only on leaderboard/win rate/APY.

### Track F — capital ladder planner
- [ ] Make targets/currency/venue sequence configurable.
- [ ] Calculate reconciled net equity and deployable capital separately.
- [ ] Add reserve and aggregate risk limits.
- [ ] Generate transfer proposals with fees, minimums, destination compatibility and expected balances.
- [ ] Implement transfer intent ledger/idempotency/reconciliation in simulation first.
- [ ] Add tests for unknown transfer outcome, restart recovery, duplicate prevention, minimums, fees and insufficient reserves.
- [ ] Keep all real transfer execution disabled until a separately reviewed capability and explicit approval are implemented.

### Track G — dashboard and reports
- [ ] Add opportunity shortlist with provenance/expiry/eligibility/net estimate/risks.
- [ ] Add capability audit and blockers.
- [ ] Add capital ladder proposals, not silent transfer execution.
- [ ] Keep operational venue health distinct from economic evidence.
- [ ] Keep mobile layout accessible and readable; show timestamps and evidence status.
- [ ] Export deterministic reports without secrets/private data.

### Track H — desktop/Android capability roadmap
- [ ] Build a documented capability matrix by platform, OS, interface and permission scope.
- [ ] Confirm install/bootstrap, device pairing, authorized emulator/device workflow and user-assisted security prompts.
- [ ] Add read-only app/page inventory before considering interaction.
- [ ] Add safe action adapters only after capability proof, terms review, risk gates and tests.
- [ ] Never imply APK execution, order submission or full-site traversal unless tested.

### Track I — PAPER evidence and operational reliability
- [ ] Verify actual collector outputs and configured paths align with scorecard inputs.
- [ ] Keep collecting public market data; monitor freshness, timestamps, gaps, reconnects and disk growth.
- [ ] Run calibration, chronological OOS, walk-forward, regime and stressed-cost studies when adequate outcomes exist.
- [ ] Keep missing/insufficient evidence distinct from a failed strategy.
- [ ] Verify Windows install/EXE workflows and real local startup behavior before declaring the node operational.

### Track J — later REAL review (not currently authorized)
- [ ] Establish explicit evidence thresholds and review checklist, including economic and operational criteria.
- [ ] Confirm account permissions, order/transfer reconciliation, emergency stop, limits and recovery.
- [ ] Require explicit human approval scoped to the capability and account.
- [ ] Run all existing independent readiness, preflight, Risk Engine, RealModeGuard and reconciliation gates.
- [ ] No automatic transition to REAL; no live action until separately authorized and verified.

## 14. Definition of done for future work

A task is not complete merely because code was written. It is complete only when:
- the change is on a dedicated branch and PR;
- code, tests and documentation agree;
- the diff is reviewed for safety, secrets and scope;
- required CI passes on the exact PR head;
- merge is verified and resulting main SHA is recorded;
- post-merge CI is checked and accurately reported;
- context/roadmap records remaining blockers and next action.

## 15. Copy/paste continuity prompt

Continue working on `AndreVazao/VazaoSovereignTrader` in Portuguese (Portugal), with a warm and direct collaborative tone. First read `docs/PROJECT_CONTEXT.md`, `docs/MASTER_ROADMAP_AND_AGREEMENTS.md`, and `docs/OPPORTUNITY_DISCOVERY_AND_CAPITAL_LADDER.md` from live `main`; then verify current main SHA, open PRs, branch state and CI. Do not assume any status in the docs is current without checking GitHub. Work autonomously on safe engineering tasks using a dedicated branch and PR, never commit normal work directly to main. Next implementation should be a typed opportunity schema/evidence-state model with unit tests, expiry/provenance validation and no execution side effects. Preserve PAPER default, all existing readiness/preflight/Risk Engine/RealModeGuard/reconciliation/operator-approval gates, human handling of MFA/CAPTCHA, least-privilege access and no secrets in logs. Do not enable REAL trading, transfers, native bots, copy-trading subscriptions or financially binding reward actions merely because a target is reached or an opportunity looks promising. No cloud resources, paid services or deployment without explicit authorization. Inspect the full diff; merge only if exact-head required CI is green and there are no blocking defects; verify post-merge workflows; update PROJECT_CONTEXT and this roadmap with exact SHAs, PRs, test results and blockers. The product objective is a dependable PAPER-first research node, evidence-backed platform audit across browser/desktop/Android, legitimate opportunity discovery, transparent mobile-friendly dashboard and eventually a configurable 1→10→100→1,000 capital ladder with explicit approval and reconciliation.


## 16. Implementation progress — opportunity registry (branch in progress)

As of 2026-10-02, branch `feat/opportunity-registry-schema` contains the first typed opportunity evidence registry:
- `PC_ENGINE/opportunity/registry.py`: typed category/status enums, record validation, explicit transition allowlist, expiry checks, positive-estimate requirements, HTTPS source provenance, PAPER-only/execution-disabled invariants and append-only JSONL persistence.
- `tests/test_opportunity_registry.py`: provenance, timestamps, state transitions, expired records, no-execution invariants, persistence and malformed-line tests.
- `docs/OPPORTUNITY_REGISTRY.md`: schema contract, state semantics, persistence, limitations and safety boundaries.
- This is not merged yet. CI and PR must be checked against the final exact head. No account ingestion, dashboard integration or execution adapters were added.


## 17. Official-source policy boundary — merged in PR #321 (2026-10-02)

PR #321 merged this increment. It is limited to local validation and provenance metadata, not network ingestion:
- Exact-host HTTPS allowlist supplied explicitly by caller; empty allowlist fails closed.
- Reject deceptive suffix hosts, embedded credentials, nonstandard ports, IP-literal hosts and fragments.
- Validate positive integer observation/capture timestamps and lowercase SHA-256 evidence digest.
- Reject cross-origin final URLs; even another allowlisted host is not trusted as an automatic redirect destination.
- Generate deterministic evidence fingerprints without persisting page contents.
- No HTTP requests, browser login, account data, crawling, claims, orders, transfers or REAL authorization.

The fetch/cache adapter, content size/type/time limits, source freshness and expiry sweeps remain future work and must have dedicated tests before any network access is enabled.


## 18. Next bounded source-ingestion increment

Implement a separate read-only public-source fetch/cache adapter only after the source policy boundary is available on main. Require explicit invocation; no background crawl by default. Apply connect/read timeouts, response-size and content-type limits, bounded redirects with exact-origin revalidation, rate limits, canonical URL/source hashing, cache freshness/expiry, and explicit unavailable/stale/unknown states. Treat all retrieved text as untrusted input. Add deterministic tests with mocked transport; never access private account pages, bypass security challenges, store credentials, or trigger financial actions.


## Official source ingestion security hardening — 2026-10-02

The current-main implementation branch `fix/official-source-ingestion-security` adds a bounded, opt-in fetcher for reviewed public official sources, with exact HTTPS host/path allowlists, redirect and response-size limits, accepted content types, timeout, SHA-256 provenance, and raw-byte output only. Security hardening rejects IP literals and obvious local hostnames, enforces path segment boundaries, rejects encoded/backslash/dot-segment paths and cross-origin redirects, and validates supplied timestamps as positive integers. Regression tests are mocked and must be verified in exact-head CI. DNS answers are not pinned or checked against private ranges; do not accept untrusted source definitions. This component does not parse content, establish account eligibility, mutate the opportunity registry, or authorize execution.


## Verification checkpoint — PR #324 merged (2026-10-02)

- PR #324, `fix: harden official source ingestion URL boundaries`, was squash-merged to main as `5e6c32543e217bec8081387b6de20589f92eec1f` after the exact PR-head workflows passed.
- Python tests run `37057829953`: SUCCESS. Windows EXE/installer run `37057829970`: SUCCESS; both EXE and installer smoke-test steps succeeded.
- The module remains an explicitly invoked, bounded read-only fetch primitive. No content parsing, registry mutation, dashboard integration, account probing or financial execution was added.
- Follow-up before broadening ingestion: implement/assess DNS resolution validation and network egress restrictions; only reviewed public official host definitions are permitted until then. Later increments should add cache freshness/expiry, rate limiting, and explicit stale/unavailable/unknown states with deterministic tests before any automated polling.


## DNS preflight increment — pending review (2026-10-02)

Branch `fix/source-ingestion-dns-preflight` adds pre-connection DNS validation to reject failed/empty resolution and any non-global IP answer, with mocked tests for private and mixed answer sets. This is defense-in-depth only, not DNS pinning: the standard urllib transport may resolve again at connect time. Do not merge until exact-head Python and Windows workflows pass. The next security step is transport-level validated-IP pinning with TLS SNI/hostname verification plus network egress restrictions.


## DNS pinned transport increment — pending review (2026-10-02)

Branch `fix/source-ingestion-pinned-transport` replaces the DNS preflight-only transport gap with a validated-IP HTTPS connection. The fetcher pins the TCP dial to the validated public address while retaining the original hostname for TLS SNI/certificate verification, disables ambient HTTP(S) proxy configuration for this path, and rejects proxy tunneling. Regression tests cover the IP dial and TLS hostname invariants. Exact-head Python and Windows workflows are required before merge. Host/network egress controls remain defense-in-depth beyond this application-layer boundary.

## 19. Recovery crash-window hardening ? PR #359 merged 2026-10-06

The recovery audit found a concrete durability window between the primary and backup snapshot writes. If a process stopped after the primary write but before the backup write, the pending reconciliation journal could otherwise be considered complete while the backup still contained an older generation.

PR #359 closes this by making reconciliation commit inspect both snapshots every time and repair the backup whenever it is missing, invalid or not equal to the durable target before the journal is cleared. A regression test simulates a crash immediately after the primary write and verifies restart recovery converges primary and backup to the same integrity digest.

Verification:
- PR #359 squash-merged to main as 162bdf61a7b19b6e721de9642acce7250e0713ea.
- Local targeted recovery/durability tests: **10 passed**.
- Hosted exact-head Python suite 37503646116 against e4c0b5f8e27b3dafa91a96560a2d05ea50637d3a: **SUCCESS**.
- No REAL order, cancellation, transfer or capital authorization was added or changed.

Next recovery audit remains end-to-end crash/restart semantics for UNKNOWN order results, partial fills, reconciliation mismatches and SAFE_MODE transitions.


## 2026-10-07 — SAFE_MODE mutation audit checkpoint / PR #376

- PR #376 merged as `953a8bd7db3e26f0d59a01abc41fe6a74a34484a`.
- Full status mutation audit identified and closed a fourth implicit SAFE_MODE exit: `SovereignEngine.stop()` previously forced SAFE_MODE to OFF.
- Stop now preserves SAFE_MODE while still stopping workers and persisting the protected runtime state.
- Regression coverage verifies in-memory and persisted SAFE_MODE survive stop.
- Current closed exit inventory: startup normalization, `pause(False)`/API resume, autonomous PAPER→REAL promotion, and stop.
- Local account-reconciliation suite remains inconclusive/stalled in the existing Windows environment; no green claim made. No hosted Actions consumed.
- No REAL authorization/execution/transfer capability changed.
- Next: enumerate all remaining status mutation paths, then harden `recover_from_safe_mode()` so readiness/reconciliation/timing evidence is independently generated, fresh, and verifiable rather than caller-supplied booleans.


## 2026-10-07 — SAFE_MODE mutation proof / recovery evidence checkpoint

- Current product main: `8a20e6ca099d0ec0917e9f38b399e2f24032cd49`.
- Exhaustive production status-mutation inventory completed. No additional SAFE_MODE exit bypass found after #376.
- The invariant is now source-audited: only `recover_from_safe_mode()` can clear SAFE_MODE.
- Added `docs/SAFE_MODE_STATE_MUTATION_AUDIT_2026-10-07.md`.
- Recovery no longer accepts caller-supplied readiness/reconciliation/timing booleans. It generates preflight, readiness, reconciliation and timing evidence internally and checks freshness before clearing the latch.
- Added authenticated `POST /safe-mode/recover`; explicit human confirmation remains required.
- REAL recovery requires fresh REAL human authorization in addition to the independently generated evidence.
- Validation is local-first: compile + diff-check passed; pytest remains inconclusive/stalled and is not classified green.
- No REAL execution/capital capability was enabled.


## 2026-10-07 — Focused recovery validation + REAL caller-path checkpoint

- Product main current checkpoint advances beyond the #376 baseline with hardened SAFE_MODE recovery evidence and the REAL caller-path fix described below.
- Added docs/REAL_AUTHORIZATION_CALLER_PATH_AUDIT_2026-10-07.md.
- Audited production REAL entry callers: /real/arm, /real/disarm, /start, /mode, autonomous PAPER→REAL promotion, and recover_from_safe_mode().
- Found and fixed an internal /mode REAL authorization sequencing bug: the route checked can_enable_real() but did not consume the one-shot authorization required by SovereignEngine.set_mode("REAL"). The route now consumes immediately before the guarded transition and fails closed on consumption failure.
- Focused SAFE_MODE recovery contract validation: 7 tests passed. These cover stale readiness, failed preflight, stale/required timing, missing fresh REAL authorization, explicit recovery, and PAPER gate preservation.
- Full account-reconciliation pytest remains an environmental stall and is not classified green.
- REAL execution/capital operations remain forbidden; no authorization is created automatically.
