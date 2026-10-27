# Cross-Organization Provenance: Repository Audit and Safe Implementation Plan

**Status:** audit of the repository source on `main` after PR #503. This document does not claim provenance or organization registration is implemented end-to-end.
**Safety:** PAPER/read-only. No production database migration, cloud provisioning, or live trading action is performed by this change.

## Executive finding

The shared-learning API is an authenticated, allow-listed aggregate-artifact store, but it does not yet have a trusted organization/installation/agent registry. Cross-user artifact retrieval is already enabled, so attribution must be introduced as a server-verified contract rather than trusting fields supplied by a client.

Do not add `organization_id`, `installation_id`, or `agent_id` to the accepted artifact payload and treat them as verified merely because the JSON contains them. The current user token authenticates a Supabase account; it does not by itself prove ownership of a VST organization, an installation key, or an agent identity.

## Verified source findings

### Artifact API

Source: `cloud/shared-learning/app/api/v1/artifacts/route.ts`.

- Both POST and GET require a Supabase Auth bearer token and call `auth.auth.getUser(token)`.
- POST bounds the request body, validates the aggregate artifact with `validateArtifact`, maps it through `publicPayload`, hashes the public payload, and persists it to `shared_learning_artifacts`.
- The database owner is taken from the verified user ID, not from request JSON.
- Duplicate uploads are deduplicated by `owner_id,artifact_digest`.
- GET returns eligible, unexpired public payloads across owners. The returned payload currently does not include a trusted contributor envelope.
- The route does not resolve organization membership, installation identity, agent/department registration, installation signatures, or artifact lineage.

### Current database boundary

Migrations inspected:

- `202609280001_shared_learning_artifacts.sql`: artifact row has `owner_id`, digest, public JSON payload, eligibility and expiry. RLS is enabled; anon/authenticated table access is revoked and server routes use the service role.
- `202609290001_identity_devices_vault_config.sql`: `user_profiles`, `reserved_usernames`, `authorized_devices`, configuration, vault and security-audit tables exist. `authorized_devices` is attached to a user and has a public key/status, but there is no organization membership, VST installation registry, agent registry, or artifact-provenance relation in these migrations.
- Later device-proof, rate-limit and endpoint-lease migrations address device/endpoint security; those concepts must not be silently conflated with organization or agent identity.

The cloud device UUID, Supabase user UUID, local PC pairing ID, VST installation ID, organization ID and agent ID must remain distinct identifiers with explicit reviewed mappings.

### PC adapter boundary

Source: `PC_ENGINE/core/vercel_shared_intelligence.py`.

- `CLOUD_FIELDS` is a strict allow-list for aggregate learning fields.
- The adapter deliberately omits local owner/device provenance.
- It sends artifacts over HTTPS with bounded timeout/response handling and only uploads eligible, unexpired artifacts.
- It cannot currently supply verified provenance because the cloud API has no trusted registry contract to validate it against.

This privacy boundary is correct and must be preserved. Do not expose local owner IDs, device pairing tokens, private endpoint addresses, credentials, account state, or private operational logs as a shortcut to attribution.

## Required trust model

The server, not client-provided display names, must determine attribution.

1. Authenticate the account with Supabase Auth.
2. Resolve an organization membership from a server-owned registry and require explicit permission to publish to the cross-organization pool.
3. Resolve an approved installation registered to that organization. Enrollment must bind proof-of-possession to a public key and have explicit approval/revocation semantics.
4. Resolve the contributor agent and department under that installation. Human-readable labels are display metadata only.
5. Bind artifact provenance to canonical IDs, a canonical payload digest, schema/producer version and timestamps. Verify a signature or another reviewed proof that the enrolled installation attests to this artifact.
6. Preserve source lineage when artifacts are derived or re-shared. Original contributor, derivative author, and validator/reviewer must be separate fields.
7. Apply expiry, revocation, eligibility and validation-state checks on reads as well as writes. Cross-organization GET must never reveal private database columns or tenant-private records.

A name such as “Joana — organization João Pedro — installation JP-PC-01 — Market Radar” may be shown only after those values have been resolved from trusted records. It must not become an authorization mechanism.

## Safe implementation sequence

### Phase 1 — identity registry and membership
- Design normalized organizations, organization memberships, installations, agents and departments with immutable UUIDs.
- Link authenticated accounts to organizations through explicit membership/role rows; never accept membership from request JSON.
- Bind installation enrollment to the existing device proof-of-possession lifecycle without reusing device IDs as installation IDs.
- Define administrator approval, revocation, name collision handling, audit events and deletion/retention rules.
- Add migration-level uniqueness and foreign-key constraints and tests for cross-organization isolation.

### Phase 2 — signed artifact provenance
- Define a versioned public envelope separate from the aggregate strategy payload.
- Derive owner and organization authority server-side; resolve installation/agent/department IDs against approved records.
- Canonicalize the signed bytes and digest before signature verification. Reject unknown provenance fields, mismatched IDs, revoked identities, stale timestamps and invalid signatures.
- Keep source lineage and contributor/validator roles distinct. Define backward compatibility for legacy artifacts: un-attributed legacy records must remain explicitly “legacy/unverified”, never be assigned a guessed contributor.
- Ensure deduplication is stable across retries and does not allow one organization to overwrite another organization's artifact.

### Phase 3 — client and operator integration
- Update the PC adapter only after the cloud schema and API are tested; transmit only the minimal verified public envelope.
- Display origin organization, installation, agent, department, contribution time, source lineage, confidence/sample size, validation, expiry and revocation state.
- Keep internal organization memory on its own local/runtime or authenticated intra-organization replication path. Do not route local department messages through this cross-organization API.
- Treat shared artifacts as research evidence only. They never confer CEO authority, membership, credentials, balances, orders, risk overrides or execution permission.

### Phase 4 — acceptance gates
- Missing/invalid token, non-member, pending/revoked installation, unknown agent and cross-org impersonation are denied.
- Client cannot claim another organization by changing a JSON field or display name.
- Same display names in different organizations remain unambiguous and cannot collide at the identity level.
- Signature/digest mismatch, replay, malformed lineage, revoked provenance, expired artifacts and unknown schema versions are rejected or quarantined.
- Cross-org reads return only eligible, unexpired public artifacts plus the verified minimal provenance envelope.
- Legacy artifacts remain clearly unverified until independently validated.
- Cloud outage leaves local memory and local department messaging functional; queued publication is durable, deduplicated and revalidated on reconnect.
- Automated tests run in PAPER/read-only and produce no external trading side effects.

## Release blockers

- No trusted organization/install/agent registry has been verified in the current migrations.
- The artifact route currently has no provenance verification or lineage logic.
- No end-to-end client-to-cloud provenance test has been demonstrated.
- Migrations have not been applied to a production Supabase project as part of this audit.
- Vercel deployment readiness does not prove database migration state or end-to-end identity enrollment.

Until those blockers are closed and the tests pass, cross-organization shared learning may remain an authenticated aggregate artifact pool, but it must not be represented in the UI as fully attributable to a verified organization/agent.


## Implementation checkpoint — provenance contract scaffold

A pure, unit-testable provenance contract has now been added at `lib/provenance.ts`, with tests in `tests/provenance.test.ts`.

It validates a strict envelope (immutable-ID-shaped UUIDs, payload digest, timestamps, bounded lineage and unknown-field rejection), defines deterministic signed bytes, calculates a SHA-256 digest of the public payload, and verifies a signature against a caller-supplied registered public key. RSA/EC-style SHA-256 signatures and Ed25519/Ed448 signatures are handled according to key type.

**Important integration boundary:** this scaffold is not yet called by `app/api/v1/artifacts/route.ts`; that route still accepts the legacy artifact schema and does not verify registry-backed identities. A key supplied by the client must never be passed as the trusted key. The future route must first resolve an approved installation and its public key from server-owned registry records, verify organization membership and agent/department ownership, and bind the digest to the exact normalized public payload.

The current branch has not demonstrated CI for these new tests yet. Do not merge or describe attribution as active until registry tables, route integration, database migration tests and end-to-end negative tests are complete.


## Database registry scaffold added on this branch

Migration `supabase/migrations/202610270001_organization_scoped_provenance.sql` now defines server-mediated tables for:

- `trader_organizations` and `trader_organization_memberships`
- `trader_installations` with a public-key fingerprint, approval/revocation state, and organization-scoped uniqueness
- `trader_departments` and `trader_agents`, with composite foreign keys preventing an agent or department from being attached to a different organization than its installation
- `shared_learning_provenance`, linked to a stored artifact and the organization/install/agent/department identities, with signature, digest, lineage, verification and revocation state

All new tables have RLS enabled, no direct anon/authenticated grants, and service-role-only grants, consistent with the existing server-mediated data model.

### Migration safety and remaining work

- The migration is only committed to the feature branch. It has **not** been applied to Supabase or production.
- The migration deliberately creates no active organization, membership, installation, or agent; enrollment and approval must be explicit.
- The existing artifact route and PC adapter are not yet wired to this registry. Therefore the schema alone does not establish verified provenance.
- Before integration, add migration/schema tests for cross-organization foreign-key rejection, unique installation key fingerprints, role/state constraints, RLS/grants, and revocation behavior.
- Route integration must validate the authenticated user's active membership and publishing role, resolve approved installation public key server-side, confirm agent/department belong to the same organization, verify the canonical payload digest and signature, and persist artifact + provenance atomically. A client-supplied public key is never trusted.
- GET response compatibility must be handled deliberately: preserve the existing adapter contract or version it. Do not silently append fields to the current strict artifact payload. Until the adapter supports provenance, continue treating legacy artifacts as unattributed/unverified in the client.
