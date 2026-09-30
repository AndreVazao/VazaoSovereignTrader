# VAZAO SOVEREIGN TRADER — PROJECT CONTEXT & CONTINUATION PLAN

Last updated: 2026-09-30 (UTC) — updated with device proof-of-possession implementation in progress
Repository: https://github.com/AndreVazao/VazaoSovereignTrader
Project: Pessoal programação
Owner's language/tone: Portuguese (Portugal), direct, collaborative; user often says “irmão”.
Purpose: durable handover for new ChatGPT conversations. Update this file whenever meaningful work is completed, a PR/CI status changes, or priorities change.

## 0. Mandatory rules for every new chat

1. Read this file first from the repository, including the PR branch if it is not yet on main. Check the live GitHub PRs, branch head SHA, CI status, and repository state before acting on stale details here.
2. Continue the roadmap in order, doing safe repository/code work autonomously without repeatedly asking broad permission. Report material progress clearly in Portuguese.
3. Always work on a dedicated branch and open/update a PR. Never push directly to main for normal feature work.
4. Never merge a PR unless André explicitly authorizes the merge or clearly instructs to do it. A green CI alone is not merge authorization.
5. Never create Supabase/Vercel/cloud resources, deploy, incur costs, or provision real user accounts without first presenting verified current costs and obtaining explicit authorization.
6. Never expose or commit passwords, tokens, keys, API credentials, recovery codes, user balances, private trade histories, or personal account identifiers. Temporary onboarding password discussed by owner must never be put in source/docs/logs.
7. Fail closed. No automatic or manual shortcut may bypass local risk controls, readiness checks, preflight/reconciliation, RealModeGuard, or PAPER/REAL gates. No forced REAL mode. Shared learning is advisory only.
8. Each owner should have their own Tailscale tailnet by default. Network membership is not permission to share private trading data. Cloud learning may contain only allow-listed aggregated technical artifacts.
9. Do not claim a deployment, account, migration, test, merge, or resource exists unless verified.
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

## 5. Current open PR #219 — onboarding, sync and vault foundations

PR: https://github.com/AndreVazao/VazaoSovereignTrader/pull/219
Title: `feat: secure owner onboarding and device vault foundations`
Branch: `feat/secure-onboarding-foundation-clean`
Base: `main`
PR is OPEN and must NOT be merged without explicit owner authorization.
Base SHA at creation was `451c5b6c26163f6f4261ede8d9962532459ee093`.
Most recent known branch commits:
- `5310a83d5ace7080792e74ba012219ee9192cd29` — device key validation/fingerprinting hardening.
- `96a1b9cd2f90e4af5b297ba2cce0c3e0002e7347` — key validation tests.
Always fetch current live head before next change.

### Latest verified CI on SHA 96a1b9cd2f90e4af5b297ba2cce0c3e0002e7347
Checked 2026-09-30:
- Shared Learning Service run #36664921837: completed SUCCESS.
- Python tests run #36664921847: completed SUCCESS.
- Windows EXE run #36664921850: completed SUCCESS.
Re-check live CI before merge or additional changes; any new commit invalidates these results for the new head.

### PR #219 contents
- Identity/device/vault/config DB migration: `cloud/shared-learning/supabase/migrations/202609290001_identity_devices_vault_config.sql`.
- `user_profiles`: unique username, role admin/member, account state pending/active/suspended, mandatory password-change flag.
- Reserved usernames `AndreVazao` and `DiogoRocha`; reservations only.
- `authorized_devices`: public key/fingerprint, pending/approved/revoked status and timestamps.
- `configuration_versions`: global/user scope, payload/hash/signature, draft/approved/active/rolled_back/revoked statuses and audit metadata; requires real signature/approval implementation before production.
- `encrypted_vault_objects`: ciphertext-only, version, nonce, salt and digest.
- `security_audit_events`: minimal security audit metadata.
- RLS enabled and anon/authenticated access revoked; server-mediated access only.
- Device route `POST /api/v1/devices` registers a public key and always begins pending; GET lists the user's devices after activation/password rotation; DELETE revokes only a device owned by the authenticated user.
- `lib/identity.ts`: public-key validation supports Ed25519, RSA >=2048 bits, and EC prime256v1/secp384r1 only; canonical SPKI PEM SHA-256 fingerprints; UUID validation. Public key validation is NOT proof-of-possession and does not approve a device.
- Local shared-learning adapter `PC_ENGINE/core/vercel_shared_intelligence.py`: standard-library HTTPS, required URL/token, bounded timeouts/responses, allow-listed upload fields, no owner/node refs, skip expired/ineligible.
- Daily sync helpers and background maintenance worker: default daily pull/push, no blocking engine startup, jitter and exponential retry. Cloud sync stays disabled by default; verify the actual runtime integration and failure behavior before enabling.
- Vault crypto foundation `cloud/shared-learning/lib/vault-crypto.ts`: AES-256-GCM, PBKDF2-SHA-256, 310,000 iterations, random 16-byte salt, 12-byte nonce, passphrase 12–1024 chars, plaintext cap 1MB. Wrong passphrase/tampering fail closed. Client app is not yet wired end-to-end.
- Vault routes authenticate owner, require active account/password rotation complete, store ciphertext only, verify digest, owner-scope GET/DELETE, use no-store and generic errors.
- Docs include `docs/LOCAL_SOVEREIGNTY_AND_SYNC_POLICY.md` and `cloud/shared-learning/docs/INITIAL_IDENTITY_AND_ONBOARDING.md`.

### PR #219 blockers — work through in order
1. **Device proof-of-possession + approval**: design a one-time cryptographic challenge with expiry/consumption, verify signature against registered public key, prevent replay, rate-limit; separate approval route restricted to active admin server-side. Device registration must stay pending until a legitimate approval flow succeeds. Audit approval/revocation. Add tests for replay, expiry, wrong signer, non-admin, cross-user and races.
2. **Trusted account provisioning/login**: secure username→Auth mapping without account enumeration; one-time provisioning after infra approval; mandatory rotation, MFA and owner recovery; server-side role checks only. Do not hardcode any password or secret.
3. **Signed/versioned configuration**: implement canonical payload hashing, signature verification, approval workflow, audit trail, rollback/last-known-good and tests. Config cannot override local risk gates or REAL mode.
4. **Vault end-to-end client/recovery**: wire encryption to desktop/phone only after threat review; safe restore UX, device-to-device restore and key-loss recovery. Do not store exchange API secrets without a separate threat model.
5. **Sync runtime integration**: inspect actual engine/maintenance scheduling; verify daily interval, jitter/backoff, offline/airplane mode, duplicate/digest behavior, response pagination and no hot-path blocking. Cloud sync disabled by default until security and infra gates are complete.
6. **Rate limiting/abuse monitoring** for all cloud endpoints; tenant-isolation, auth expiry, RLS/grants, payload size, cross-tenant access, role escalation, audit and rollback tests.
7. Update this file and docs; run Shared Learning Service, Python and Windows EXE CI; review diff and PR metadata. Leave PR open until André authorizes merge.
8. Only after code is reviewed and merged by explicit authorization, consider infra setup: new organization first, current cost/limits and region verified, show costs, wait for explicit authorization, then provision in approved order. Do not deploy or provision accounts beforehand.

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

## 8. Current device proof-of-possession feature branch (in progress)

A stacked feature branch was created from `feat/secure-onboarding-foundation-clean`:
- Branch: `feat/device-proof-and-admin-approval`
- Latest known commit before final context update: `24f91f11263527bbc2819903a5458878219110e7` (onboarding docs); fetch live branch head before acting.
- Changes implemented so far: `verifyDeviceProof` uses Node crypto to verify signatures against the registered public key; tests cover valid Ed25519 signature, altered challenge and malformed signature. Added migration `202609300001_device_proof_and_approval.sql` with a one-time challenge table, `possession_verified_at`, and a database function that rechecks active admin role/account/password-rotation state, only approves pending devices with verified possession, and writes the audit event atomically. Added `POST /api/v1/devices/challenge`, `POST /api/v1/devices/verify`, and `POST /api/v1/devices/approve`; docs describe the flow. Challenges are 5-minute, hash-only at rest and single-use; verification consumes the challenge before checking signature to prevent replay. Device stays pending after proof until an eligible admin approves it.
- Stacked PR #221: https://github.com/AndreVazao/VazaoSovereignTrader/pull/221 (open, non-draft, base `feat/secure-onboarding-foundation-clean`, not merged). Shared Learning Service workflow run `36669360478` completed SUCCESS on code/context head `d9ceeeca22aab1b03580e78ce271d0a6cf57eea8`; `npm test` and `npm run build` both passed. Python/Windows workflows were not returned for this stacked PR and these changes are cloud-service-only. Any subsequent commit requires rechecking CI for the new head.
- Security gaps still requiring review: no rate limiting/abuse monitoring yet; no end-to-end integration tests against a disposable Supabase database; approval auth has server-side active-admin and password-rotation checks but MFA/step-up authentication is not wired; route-level failure/race behavior needs review. Do not deploy.

## 9. Immediate next action for the next chat

1. Fetch live PR #221 head SHA and verify the Shared Learning Service workflow again after this context-only update.
2. Review SQL function and routes for signature canonicalization, challenge replay/expiry/races, admin authorization, atomic audit, and Supabase RPC permissions. Add route/integration tests and rate limiting before considering production.
3. Keep PR #221 stacked on PR #219 and keep both open/unmerged unless André explicitly authorizes merge.
4. Continue with trusted account provisioning/login, MFA/owner recovery, signed configuration governance, vault restore UX, and sync runtime validation in that order.
5. Update this context file with exact PR number, branch head SHA, CI run IDs/outcomes, blockers and next action.

## 10. Original continuity prompt for a new ChatGPT conversation

You are continuing work on GitHub repository `AndreVazao/VazaoSovereignTrader` in project “Pessoal programação”. First read `docs/PROJECT_CONTEXT.md` on the current feature/PR branch, then verify live GitHub state, latest SHA and CI before acting. The active stacked feature branch is `feat/device-proof-and-admin-approval`, based on open PR #219 branch `feat/secure-onboarding-foundation-clean`. Continue with the next action in section 9, beginning by reviewing and testing the new device proof-of-possession/admin approval implementation. Work autonomously on safe code changes, always use a dedicated branch/PR, test and report in Portuguese. Do not merge without my explicit authorization. Do not create cloud resources, deploy, incur costs or provision accounts until current costs/terms are checked, presented to me, and I explicitly authorize. Never expose or commit secrets. Keep trading fail-closed; shared learning must never bypass local risk gates or authorize REAL. At the end of each work session, update `docs/PROJECT_CONTEXT.md` with current branch/head SHA, exact CI outcomes, completed work, blockers and next action so another chat can continue without losing context.

## 9. Prompt for starting a new ChatGPT conversation

You are continuing work on GitHub repository `AndreVazao/VazaoSovereignTrader` in project “Pessoal programação”. First read `docs/PROJECT_CONTEXT.md` on the current PR branch `feat/secure-onboarding-foundation-clean` (PR #219) if it is not yet on main, then verify live GitHub state, latest SHA and CI before acting. Treat the context file as the source of continuity but verify current statuses. Continue the roadmap in section 5 in order, beginning with secure device proof-of-possession and admin approval. Work autonomously on safe code changes, always use a dedicated branch/PR, test and report in Portuguese. Do not merge without my explicit authorization. Do not create cloud resources, deploy, incur costs or provision accounts until you have checked current costs/terms, presented them to me, and received explicit authorization. Never expose or commit secrets. Keep trading fail-closed; shared learning must never bypass local risk gates or authorize REAL. At the end of each work session, update `docs/PROJECT_CONTEXT.md` with current branch/head SHA, exact CI outcomes, completed work, blockers and next action so another chat can continue without losing context.
