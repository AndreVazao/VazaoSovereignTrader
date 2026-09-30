# VAZAO SOVEREIGN TRADER — PROJECT CONTEXT & CONTINUATION PLAN

Last updated: 2026-09-30 (UTC) — PR #219 merged; clean replacement PR #223 consolidates device proof, approval and rate-limit work
Repository: https://github.com/AndreVazao/VazaoSovereignTrader
Project: Pessoal programação
Owner's language/tone: Portuguese (Portugal), direct, collaborative; user often says “irmão”.
Purpose: durable handover for new ChatGPT conversations. Update this file whenever meaningful work is completed, a PR/CI status changes, or priorities change.

## 0. Mandatory rules for every new chat

1. Read this file first from the repository, including the PR branch if it is not yet on main. Check the live GitHub PRs, branch head SHA, CI status, and repository state before acting on stale details here.
2. Continue the roadmap in order, doing safe repository/code work autonomously without repeatedly asking broad permission. Report material progress clearly in Portuguese.
3. Always work on a dedicated branch and open/update a PR. Never push directly to main for normal feature work.
4. Merge autonomously when the PR is reviewed, the required CI checks are green on the exact latest head, there are no unresolved blocking failures, and the diff is within the approved project scope. Do not ask for generic merge authorization. If a PR is obsolete, duplicated, unsafe, or no longer useful, close it with a clear reason rather than leaving it open.
5. Never create Supabase/Vercel/cloud resources, deploy, incur costs, or provision real user accounts without first presenting verified current costs and obtaining explicit authorization.
6. Never expose or commit passwords, tokens, keys, API credentials, recovery codes, user balances, private trade histories, or personal account identifiers. Temporary onboarding password discussed by owner must never be put in source/docs/logs.
7. Fail closed. No automatic or manual shortcut may bypass local risk controls, readiness checks, preflight/reconciliation, RealModeGuard, or PAPER/REAL gates. No forced REAL mode. Shared learning is advisory only.
8. Each owner should have their own Tailscale tailnet by default. Network membership is not permission to share private trading data. Cloud learning may contain only allow-listed aggregated technical artifacts.
9. Do not claim a deployment, account, migration, test, merge, or resource exists unless verified.
10. Keep only one active implementation task/feature branch and its current PR wherever practical. Finish the current PR, validate it, merge it when green, then create the next dedicated branch and PR. Avoid accumulating stale open PRs; consolidate useful work, retarget stacked PRs safely, and close obsolete PRs. Delete old remote branches only when supported; André may clean them up manually afterward.
10. Before finishing a work session, update this context file (or explicitly state why it could not be updated) with completed work, exact branch/PR/SHA, test outcomes, blockers and next action.

## 1. Core objectives and architecture

- Build and harden VazaoSovereignTrader with safe, evidence-based autonomous operation.
- The engine should gather its own evidence and decide whether promotion criteria are satisfied, but promotion is never forced. PAPER → REAL must remain gated by all readiness, paper-review, authorization, preflight, reconciliation, recovery and risk controls.
- Local-first: each PC is an independent sovereign node. Safe local functionality must continue if cloud services are unreachable. Market/exchange functions still require live connectivity and must reject stale market data.
- Optional phone companion; not yet deployed/installed as part of this work.
- Proposed shared architecture: separate Vercel service + Supabase (EU region requested: eu-west-3/Paris), sharing only aggregated, allow-listed learning artifacts. No private trade ledgers, balances, orders, fills, positions, exchange credentials, or owner/device identifiers in public learning.
- Shared artifacts are untrusted advice, never commands. They cannot change risk limits, credentials, startup settings, or PAPER/REAL mode.
- No hard 20-user cap; design for expansion while enforcing tenant isolation, quotas and abuse protection.
- Local trading nodes should not depend on cloud availability.
- User wants free plans considered first, but current costs/limits and terms must be checked before resource creation. Vercel Hobby commercial-use terms require checking against current official terms if deployment is considered.

## 2. Cloud authorization and organization status — NOT AUTHORIZED TO CREATE

- User explicitly has not authorized creation/deployment of Supabase/Vercel resources yet.
- User wants to create a new organization first, then receive a cost estimate and explicitly approve before project/resource creation.
- Existing Supabase organization seen: `baribudos-studio-website`, ID `kvcpzugzzheeymkavbil`. This is not the requested new organization.
- A prior combined org/cost query returned a permission error. Next cost-estimate action to retry when relevant: Supabase get_cost for project under org `kvcpzugzzheeymkavbil`, but do not create anything.
- No confirmed new Supabase project, migration deployment, Vercel shared-learning deployment, or live accounts.
- Existing Vercel team: `AndreVazao's projects`, slug `andrevazaos-projects`, ID `team_geLzl1PR82ic1k4GRXizeM7z`.
- Existing Vercel projects observed: `devops-god-mode`, `baribudos-studio-website`, `ai-devops-control-center`, `jules-mad`. No shared-learning project observed. Do not deploy into existing projects without explicit scope and authorization.
- Target usernames reserved in source only: `AndreVazao` (intended admin) and `DiogoRocha` (member). Reservations are NOT live Supabase Auth accounts. Account provisioning must happen through a trusted one-time process only after infrastructure is approved, and must require immediate password rotation. Never store initial password in source.

## 3. Trading engine: merged work

Repository history includes merged PRs #197–#217. Key milestones:
- #197 expanded candlestick patterns.
- #198 unified candlestick evidence vocabulary.
- #199 market freshness gate.
- #200 PAPER autostart readiness.
- #201 propagate market data quality to strategy.
- #202 autonomous PAPER→REAL promotion using readiness, paper review, one-time RealModeGuard authorization, preflight/reconciliation and fail-safe behavior.
- #203 initialize RealModeGuard.
- #204 stronger readiness evidence: diversity, temporal span, recent evidence and positive economic CI.
- #205 automatic PAPER evidence ledger, out-of-sample/cost stress, dedupe windows and writer health.
- #206 read-only `/autonomous-readiness`.
- #207 cockpit readiness + paper review.
- #208 restore pending human interaction panel.
- #209 escape dynamic cockpit values.
- #210 respect switches `enabled`, `allow_real`, `auto_promote_real`.
- #211 clear stale REAL readiness if evaluation fails.
- #212 cockpit respects switches; Python CI green.
- #213 fail-safe regression tests for preflight/reconciliation failures; Python workflow green.
- #214 manual REAL `/mode` and `/start` require readiness and `paper_review.ready`; Python and Windows EXE CI green; merge SHA began `ca2173a6`.
- #215 validate persisted recovery state for REAL readiness. If positions are open, require configured recovery state file with valid JSON object, positions dict and every open position key; no file needed if no open positions. Python and Windows EXE passed.
- #216 docs for shared-learning privacy and network boundaries.
- #217 authenticated Vercel shared-learning service scaffold, squash merge SHA `451c5b6c26163f6f4261ede8d9962532459ee093`.

No promotion to REAL has been reported as occurring. Keep this true unless verified otherwise.

## 4. Shared-learning service on main (#217)

Location: `cloud/shared-learning`; designed as a separate Next.js 15 / React 19 / TypeScript service.
- `GET /api/health`
- Authenticated `POST/GET /api/v1/artifacts`
- Strict allow-list artifact fields: `schema_version`, `artifact_type`, `strategy_id`, `market`, `regime`, `horizon_seconds`, `sample_count`, `win_count`, `win_rate`, `mean_net_bps`, `median_net_bps`, `eligible`, `created_at_ms`, `producer_version`, `artifact_id`, `source_digest`, `trust_score`, `source_count`, `expires_at_ms`.
- Unknown/private fields rejected. User identity comes from verified Supabase token, never JSON. Cross-user GET returns only eligible, unexpired public payloads without owner IDs. 32KB payload cap; max page size 100.
- Migration `cloud/shared-learning/supabase/migrations/202609280001_shared_learning_artifacts.sql`: owner ID, digest, public payload, eligibility and expiry; RLS enabled, no anon/authenticated policies; server service role only after Auth validation.
- Production requires Supabase project, migration application and policy verification, Vercel environment variables, preview security tests, rate limiting and abuse monitoring.
- Snapshot API currently bounded (no cursor pagination).
- Current production runtime sync must not be enabled until all security blockers are closed.

## 5. Merged PR #219 — onboarding, sync and vault foundations

PR #219: https://github.com/AndreVazao/VazaoSovereignTrader/pull/219
Status: MERGED on 2026-09-30.
Merge commit on `main`: `ba7f916d99be92df1a67e2237f51bdd782b3d59a`.
The exact PR head `147039106c7b4fa8a850ac8a128b4e76b96f6aa9` had successful Shared Learning Service, Python tests, and Windows EXE workflows before merge.

Merged foundations include identity/device/vault/config schema; reserved usernames only (not active accounts); per-device registration/revocation; privacy-allow-listed shared-learning adapter; daily local-first sync helpers and background worker; client-side encrypted vault helpers/routes; key-strength validation; local sovereignty policy; and durable project context.

Security boundaries remain:
- Cloud sync disabled by default; cloud advice never replaces local risk controls.
- No cloud resources, deployments, accounts or costs created.
- End-to-end vault recovery, trusted account provisioning, MFA, signed configuration lifecycle, live sync scheduling validation, and database integration tests remain incomplete.
- No PAPER→REAL promotion or RealModeGuard bypass.
- Infra provisioning/deployment still requires current cost/terms review and André's explicit authorization.

## 6. Closed accidental PR #220

PR #220: https://github.com/AndreVazao/VazaoSovereignTrader/pull/220
Branch `fix/device-public-key-strength`; it accidentally had an excessively broad diff and was closed unmerged. Do not reopen it. Correct key-hardening work was copied onto PR #219's actual head branch. An intermediate test used unsupported `secp192r1`; fixture was changed to `secp224r1` and tests on current PR #219 passed. Keep all further work on the correct PR #219 branch or a dedicated clean branch.

## 7. Privacy and network policy

Reference: `docs/SHARED_INTELLIGENCE_PRIVACY_AND_NETWORK.md`.
- Tailnet is a network trust boundary, not a shared database authorization boundary.
- Separate tailnets per owner by default.
- Only explicitly allow-listed aggregated technical learning is shareable.
- Keep credentials, balances, account IDs, orders/fills/positions/trade histories/ledger rows, owner/device refs and sensitive logs private.
- Server-side tenant identity and authorization; client and server allow-list validation; quotas/payload limits; no cross-tenant read/delete; TLS, secret storage/rotation, audit and fail-safe sync.
- Imported artifacts are untrusted advice.
- Source code does not prove a live deployment/database has correct tenant isolation.

## 8. Current active PR #223 — device proof, approval and rate-limit hardening

PR: https://github.com/AndreVazao/VazaoSovereignTrader/pull/223
Branch: `feat/device-proof-and-approval-clean`
Base: `main`
Latest code commit before this context refresh: `3b656edd7148cc74e181a3e72137a848b8c45823`. This context refresh creates a new head SHA, so CI must be rechecked on that new exact head before merging.

PR #223 is a clean consolidation of useful work from old stacked PRs #221 and #222 onto the merged #219 foundation. It currently changes 9 files relative to main. PR #221 and PR #222 have been closed as superseded; do not reopen them unless the replacement PR is found incomplete.

Implemented in the active PR:
- Short-lived, single-use device proof challenges; public-key signature verification and atomic challenge consumption.
- Admin-only approval with database-side active-account/admin/password-rotation checks, verified-possession requirement, audit event, and explicit prevention of approving one's own device.
- Database-backed atomic per-account fixed-window rate limits: device registration 10/5 minutes, challenge issuance 10/5 minutes, proof verification 8/5 minutes, administrator approval 20/5 minutes. Routes fail closed if the limiter RPC fails and return HTTP 429 when over limit.
- Signature tests for Ed25519, RSA-2048, P-256 and P-384; onboarding/rate-limit documentation.
- Local-first sync and vault foundations remain those already merged in #219; full phone/PC restore is not complete.

PR history:
- PR #219 merged to main at `ba7f916d99be92df1a67e2237f51bdd782b3d59a`.
- PR #221 closed as superseded by #223, not merged.
- PR #222 closed as superseded by #223, not merged.
- PR #223 is the only active implementation PR and must be kept current.

CI verified on code head `3b656edd7148cc74e181a3e72137a848b8c45823`:
- Shared Learning Service run `36671619790`: SUCCESS (`npm test` and `npm run build` passed).
- Python tests run `36671619770`: SUCCESS.
- Python tests run `36671615586`: SUCCESS.
The earlier head `4edf5ac87edebf91dd38f7e421b15a41b33c0555` failed Shared Learning tests because the proof-verification helper was missing from the clean transplant; the helper was restored from the validated feature branch and the tests above passed on the corrected code head. This context-only update creates a new head and therefore requires fresh CI before merge.

Remaining security blockers before production:
1. Validate migration SQL and RPC behavior with integration tests, including RLS, service-role grants, tenant isolation, expiry, replay, concurrent consumption/approval, and audit outcomes. Do not create Supabase resources until current costs/terms are reviewed and André explicitly authorizes it.
2. Add MFA/step-up authentication for administrative approval.
3. Add edge/WAF rate limits and abuse monitoring/alerting; database limits are only per authenticated account.
4. Complete secure account provisioning/login, mandatory credential rotation, owner recovery, signed/versioned configuration with approval and rollback, end-to-end vault recovery, and actual offline/daily sync runtime validation.
5. Keep cloud sync disabled by default and preserve local risk gates. No cloud project, deployment, account provisioning or paid resource has been created.

## 9. Immediate next action

Fetch the current PR #223 head and exact-head CI. Fix any failures, run/review the applicable Shared Learning Service, Python and Windows EXE workflows, and inspect the final diff. Merge automatically only when the exact latest head's required CI is green, the PR is mergeable, and review reveals no blocking defect. Then close any superseded PRs, update this context on main through the normal branch/PR flow, and open one fresh dedicated branch/PR for the next roadmap task. Keep only one active implementation PR wherever practical.

## 10. Original continuity prompt for a new ChatGPT conversation

You are continuing work on GitHub repository `AndreVazao/VazaoSovereignTrader` in project “Pessoal programação”. First read `docs/PROJECT_CONTEXT.md` from the newest relevant branch, then verify live GitHub state, PR #223, latest SHA and CI before acting. PR #219 is merged; old PRs #221/#222 are closed as superseded. Continue with the next action in section 9. Work autonomously on safe code changes, always use a dedicated branch/PR, test and report in Portuguese. Merge when the exact latest head has green required CI and review reveals no blocking issue; close obsolete PRs instead of leaving them open. Do not create cloud resources, deploy, incur costs or provision accounts until current costs/terms are checked, presented to me, and I explicitly authorize. Never expose or commit secrets. Keep trading fail-closed; shared learning must never bypass local risk gates or authorize REAL. At the end of each work session, update `docs/PROJECT_CONTEXT.md` with current branch/head SHA, exact CI outcomes, completed work, blockers and next action so another chat can continue without losing context.

## 11. Prompt for starting a new ChatGPT conversation

You are continuing work on GitHub repository `AndreVazao/VazaoSovereignTrader` in project “Pessoal programação”. First read `docs/PROJECT_CONTEXT.md` from the newest relevant branch, then verify live GitHub PR #223, latest SHA and CI before acting. Treat this context as durable continuity but verify all live statuses. Continue the roadmap in order, beginning by completing CI validation and the security review/integration-test plan for device proof-of-possession, admin approval and rate limiting. Work autonomously on safe code changes, always use a dedicated branch/PR, test and report in Portuguese. Merge when the exact latest head has green required CI and review reveals no blocking issue; close obsolete PRs instead of leaving them open. Do not create cloud resources, deploy, incur costs or provision accounts until you have checked current costs/terms, presented them to me, and received explicit authorization. Never expose or commit secrets. Keep trading fail-closed; shared learning must never bypass local risk gates or authorize REAL. At the end of each work session, update `docs/PROJECT_CONTEXT.md` with current branch/head SHA, exact CI outcomes, completed work, blockers and next action so another chat can continue without losing context.
