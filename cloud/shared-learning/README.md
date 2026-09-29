# Vazao Sovereign Trader — Shared Learning API

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
- `GET /api/v1/devices`: list the authenticated user's devices after account activation and mandatory password rotation.
- `DELETE /api/v1/devices?id=<uuid>`: revoke only a device belonging to the authenticated user.

## Database migrations
1. `supabase/migrations/202609280001_shared_learning_artifacts.sql`
2. `supabase/migrations/202609290001_identity_devices_vault_config.sql`

The second migration reserves the exact usernames `AndreVazao` (intended administrator) and `DiogoRocha` (member). These are reservations only, not live Auth accounts. No passwords are included in source control. See `docs/INITIAL_IDENTITY_AND_ONBOARDING.md`.

## Setup required before production
1. Create the Supabase project in the intended organization and EU region, after cost/organization confirmation.
2. Apply both migrations and verify RLS and grants.
3. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in Vercel server-side environment variables only.
4. Import this repository into Vercel and set Root Directory to `cloud/shared-learning`.
5. Implement and test trusted account provisioning, mandatory password rotation, MFA/owner recovery, a secure pending-device approval/proof-of-possession flow, configuration signing/approval/rollback, and client-side vault encryption before onboarding. Registration and owner-scoped revocation endpoints exist; approval and proof-of-possession remain blockers.
6. Deploy a preview and test invalid/missing tokens, private fields, duplicates, expiry, cross-tenant access, role escalation, device revocation, vault confidentiality, and rollback.
7. Configure rate limiting and abuse monitoring before broad rollout.

## Production blockers
Source code alone does not provision a database or deployment. Reserved usernames are not usable accounts. The initial temporary credential must never be committed or stored in a migration; it may only be introduced by a trusted one-time provisioning workflow after infrastructure is approved, and must be rotated before normal use.

Configuration synchronization is deliberately separate: it requires versioning, approval, audit history, signature validation and rollback, and must never override local risk or REAL-mode gates. The current branch does not create cloud resources, deploy services, enable cloud sync, or authorize live trading.


## Local sovereignty
Each PC is a local-first node and must continue safe local work when cloud services are unreachable. Cloud sync is optional, best-effort maintenance and defaults to daily pull/push intervals. See [Local Sovereignty and Background Synchronization](../../docs/LOCAL_SOVEREIGNTY_AND_SYNC_POLICY.md). Daily interval helpers exist, but runtime scheduler integration, jitter/backoff, and airplane-mode validation remain required before enabling production sync.
