# Vazao Sovereign Trader — Shared Learning API
Deploy this directory as a separate Vercel project with Root Directory `cloud/shared-learning`.

## Scope
- Authenticated API using Supabase Auth access tokens.
- Strict allow-list for aggregate learning artifacts; unknown/private fields are rejected.
- Tenant ownership is derived from the verified Supabase user, never request JSON.
- Cross-user reads return only eligible, unexpired public payloads, without owner IDs or database columns.
- No endpoint changes startup settings, risk limits, exchange credentials, or PAPER/REAL mode.
- Shared intelligence is advisory; local trading gates remain authoritative.

## Endpoints
- `GET /api/health`: non-sensitive health check.
- `POST /api/v1/artifacts`: submit one artifact, with `Authorization: Bearer <Supabase access token>`.
- `GET /api/v1/artifacts?limit=50`: retrieve eligible, unexpired artifacts with the same authentication.

## Setup required before production
1. Create the Supabase project in the intended organization and EU region.
2. Apply `supabase/migrations/202609280001_shared_learning_artifacts.sql`.
3. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in Vercel server-side environment variables only.
4. Import this repository into Vercel and set Root Directory to `cloud/shared-learning`.
5. Deploy preview and test invalid/missing tokens, private fields, duplicates, expiry, and cross-tenant reads.
6. Configure user invitation/registration policy in Supabase Auth before onboarding users.

## Production blockers
Source code alone does not provision a database or deployment. Rate limiting and abuse monitoring must be configured before broad rollout. Configuration synchronization is deliberately separate: it requires versioning, approval, audit history, and rollback, and must never override local risk or REAL-mode gates.
