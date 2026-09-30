# Vazao Sovereign Trader — Shared Learning API

**Project continuity:** See [docs/PROJECT_CONTEXT.md](../../docs/PROJECT_CONTEXT.md) for current architecture, verified CI, PR state, security constraints, blockers, and the ordered continuation plan. Update that file at the end of each meaningful work session.

Deploy this directory as a separate Vercel project with Root Directory `cloud/shared-learning`.

## Scope
- Authenticated API using Supabase Auth access tokens.
- Strict allow-list for aggregate learning artifacts; unknown/private fields are rejected.
- Tenant ownership is derived from the verified Supabase user, never request JSON.
- Cross-user reads return only eligible, unexpired public payloads, without owner IDs or database columns.
- Identity, device authorization, signed/versioned configuration metadata and encrypted-vault metadata are defined by the second migration.
- No endpoint changes startup settings, risk limits, exchange credentials, or PAPER/REAL mode.
- Shared intelligence is advisory; local trading gates remain authoritative.

## Endpoints
- `GET /api/health`: non-sensitive health check.
- `POST /api/v1/artifacts`: submit one artifact, with `Authorization: Bearer <Supabase access token>`.
- `GET /api/v1/artifacts?limit=50`: retrieve eligible, unexpired artifacts with the same authentication.
- `POST /api/v1/devices`: register a validated device public key; registration always starts as `pending`.
- `POST /api/v1/devices/challenge`: issue a short-lived one-time challenge for a pending device owned by the authenticated user.
- `POST /api/v1/devices/verify`: verify a signature made by the registered private key, consume the challenge once, and mark proof-of-possession verified. This does **not** approve the device.
- `POST /api/v1/devices/approve`: approve only a pending device with verified proof-of-possession; requires an active administrator profile with mandatory password rotation complete; the database function rechecks role/state and writes an audit event atomically.
- `GET /api/v1/devices`: list the authenticated user's devices after account activation and mandatory password rotation.
- `DELETE /api/v1/devices?id=<uuid>`: revoke only a device belonging to the authenticated user.

## Database migrations
1. `supabase/migrations/202609280001_shared_learning_artifacts.sql`
2. `supabase/migrations/202609290001_identity_devices_vault_config.sql`
3. `supabase/migrations/202609300001_device_proof_and_approval.sql`

The second migration reserves the exact usernames `AndreVazao` (intended administrator) and `DiogoRocha` (member). These are reservations only, not live Auth accounts. No passwords are included in source control. See `docs/INITIAL_IDENTITY_AND_ONBOARDING.md`.

## Setup required before production
1. Create the Supabase project in the intended organization and EU region, after cost/organization confirmation.
2. Apply both migrations and verify RLS and grants.
3. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in Vercel server-side environment variables only.
4. Import this repository into Vercel and set Root Directory to `cloud/shared-learning`.
5. Implement and test trusted account provisioning, mandatory password rotation, MFA/owner recovery, configuration signing/approval/rollback, and end-to-end client-side vault encryption before onboarding. The current feature branch adds one-time device proof-of-possession and audited admin approval foundations; these still require CI/security review, rate limiting, integration tests, and deployment migration validation.
6. Deploy a preview and test invalid/missing tokens, private fields, duplicates, expiry, cross-tenant access, role escalation, device revocation, vault confidentiality, and rollback.
7. Configure rate limiting and abuse monitoring before broad rollout.

## Production blockers
Source code alone does not provision a database or deployment. Reserved usernames are not usable accounts. The initial temporary credential must never be committed or stored in a migration; it may only be introduced by a trusted one-time provisioning workflow after infrastructure is approved, and must be rotated before normal use.

Configuration synchronization is deliberately separate: it requires versioning, approval, audit history, signature validation and rollback, and must never override local risk or REAL-mode gates. The current branch does not create cloud resources, deploy services, enable cloud sync, or authorize live trading.


## Local sovereignty
Each PC is a local-first node and must continue safe local work when cloud services are unreachable. Cloud sync is optional, best-effort maintenance and defaults to daily pull/push intervals. See [Local Sovereignty and Background Synchronization](../../docs/LOCAL_SOVEREIGNTY_AND_SYNC_POLICY.md). Daily throttling, a background maintenance worker, jitter, and exponential retry/backoff foundations exist in the PR branch. Before enabling production sync, verify actual engine lifecycle integration, offline/airplane-mode behavior, idempotency, and that the cloud remains disabled by default.


## Local PC sync adapter status

The PC now has a stdlib-only `VercelSharedIntelligenceProvider` adapter. It requires
`VST_SHARED_INTELLIGENCE_URL` and `VST_SHARED_INTELLIGENCE_TOKEN`, refuses non-HTTPS
URLs, bounds request timeouts and response sizes, and maps the cloud's snapshot response
to the local importer contract. Uploads use a strict field allow-list and omit local
owner/device provenance references. Expired or ineligible artifacts are not uploaded.

The API currently exposes a bounded snapshot rather than cursor pagination, so each
scheduled pull is a fresh limited snapshot. The helper's daily throttling exists, but
the production engine scheduler must still call it from a low-priority maintenance task;
cloud sync remains disabled by default until account provisioning, device approval,
rate limits, and runtime integration are complete.


## Client-side vault encryption foundation

`lib/vault-crypto.ts` provides a versioned client-side envelope using AES-256-GCM and
PBKDF2-SHA-256 with a random salt and nonce. The passphrase and derived key are not
returned by the helper. Tests cover round-trip encryption, wrong-passphrase/tamper
rejection, weak passphrases, and unsupported envelope versions.

This is a cryptographic foundation plus authenticated owner-scoped ciphertext storage routes, not a complete recovery feature: the desktop/mobile client is not yet wired end-to-end to these routes, and recovery UX, device-to-device restore, and key-loss recovery remain incomplete. Never upload plaintext or passphrases; do not store exchange API secrets in this vault without a separately reviewed threat model.
