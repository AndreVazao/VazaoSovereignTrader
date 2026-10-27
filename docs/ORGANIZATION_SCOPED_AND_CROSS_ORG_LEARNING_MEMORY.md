# Organization-Scoped and Cross-Organization Learning Memory

**Status:** architecture contract for implementation; not a claim that synchronization or global identity registration is already complete.
**Scope:** VazaoSovereignTrader only. DGM-MAT remains separate.
**Safety:** all development and tests remain PAPER/read-only. Shared learning never authorizes real trading or external side effects.

## 1. Two different memory scopes

VST must distinguish two scopes with separate APIs, storage boundaries, permissions, retention rules and observability. A generic "shared memory" label must never conceal which scope a record belongs to.

### A. Organization-internal memory

This belongs to one organization and is shared among that organization's local departments/agents and authorized installations.

- Example: organization André Vazão has its own CEO and internal departments.
- Example: organization João Pedro has a separate CEO and its own departments.
- In the current single-PC installation, modules use local runtime interfaces, events/queues and local storage/memory. They must not use network calls, Vercel or Tailscale as an internal module message bus.
- If one organization later uses several PCs, those PCs may synchronize that organization's internal memory over authenticated inter-PC transport, subject to membership and data permissions.
- Organization-private records, owner instructions, private financial state, balances, orders, credentials, personal configuration and private operational logs remain within their authorized scope unless a separate explicit export policy permits otherwise.

### B. Cross-organization shared learning

This is a separate, opt-in knowledge-sharing layer for approved, reusable trading research and learning artifacts across independent organizations.

- André Vazão's organization and João Pedro's organization remain distinct, each with its own CEO, host roster, permissions, local memory, operational state and execution authority.
- Each organization may contribute eligible learning artifacts and consume eligible artifacts from other participating organizations.
- New installations can bootstrap from the approved shared knowledge pool. An older installation may have contributed more validated knowledge, but age alone never makes a record correct or trusted.
- Every installation continues to learn and may contribute new validated findings, so the shared pool evolves in both directions.
- Sharing knowledge does not grant access to another organization's internal memory. Only explicitly eligible artifacts cross this boundary.
- Vercel or another service may host the API; Vercel is a replaceable implementation choice, not a permanent architectural dependency.

## 2. Data allowed across the organization boundary

Allowed candidates, subject to validation and policy: generalized strategy research, market/regime observations, aggregate statistics, reusable analytical findings, source references/digests, confidence, sample counts, validation status, schema/producer version and expiry.

Never publish by default: API keys, passwords, private keys, auth tokens, exchange account identifiers, balances, private order history, transfer/withdrawal data, private financial state, owner conversations, raw local logs, personal data or organization-private operating instructions.

Cross-organization artifacts must be minimized and schema-allow-listed. Reject unknown or sensitive fields rather than silently forwarding them. Sharing a strategy or statistical finding does not share execution configuration or permission to execute it.

## 3. Verifiable provenance: who contributed a finding?

Every shared artifact must make it possible to answer: who contributed it, from which organization and installation, and how was it validated?

The logical provenance envelope should include:
- stable artifact ID for deduplication;
- immutable registry-issued organization ID and human-readable organization name;
- unique enrolled installation ID;
- registry-issued agent ID and display name;
- department ID;
- signed provenance or a verifiable identity reference;
- timestamps, producer/software version and schema version;
- source reference/digest, sample count, confidence, validation status, reviewer/validator attribution where available, expiry and revocation/staleness status.

Example UI attribution: "Joana — organization João Pedro — installation JP-PC-01 — Market Radar". Another could be "Rui — organization André Vazão — installation AV-PC-01 — Investigation". These are illustrative labels; actual IDs and names must come from the registry and verified records, not an unverified free-text claim.

Attribution must survive import, re-sharing and derivation. If an organization derives a result from another organization's artifact, preserve the source lineage and identify the new contributor separately. A display name alone is not proof of authorship.

The existing shared-intelligence adapter deliberately excludes local owner/device provenance from public payloads. Do not solve attribution by leaking private local metadata. Instead, define a minimal authenticated public provenance envelope and update API schema, authorization, persistence, signatures/verification and tests together. Until that end-to-end contract exists, global attribution is not implemented.

## 4. Registration and collision-free identities

On first registration, the control plane should create or resolve the organization identity and enroll the installation. Bind these identities distinctly:
1. organization ID and organization display name;
2. owner/account identity and authorized administrators;
3. installation ID and cryptographic installation key;
4. CEO/agent ID and display name;
5. department IDs and agent IDs;
6. permissions for internal replication and cross-organization learning.

Names are labels; authorization uses immutable IDs, verified credentials and explicit membership. A registration request cannot claim another organization merely by sending its display name.

The registry must prevent identity collisions. Agent names should be globally unique in the registry or receive stable disambiguating labels such as "Joana · André Vazão · AV-PC-01". IDs remain canonical even if a display name changes. Duplicate names must never cause one installation's agent to be mistaken for another.

Target registration flow:
1. Authenticate the owner and prove possession of a newly generated per-installation key.
2. Create or select an organization the owner is authorized to administer.
3. Obtain immutable organization and installation IDs from the registry.
4. Register CEO/agent and department identities under that organization/installation.
5. Apply approval, revocation and role policies before granting access.
6. Return canonical IDs and collision-free display labels to the local system.
7. Record auditable enrollment and naming events.

A display name such as "André Vazão" is not sufficient proof of control of that organization. Audit deployed routes, database schema, authentication and approval flows before runtime integration; do not assume the current Vercel implementation already supports this entire process.

## 5. Trust and learning quality

Shared learning is not trusted merely because it came from an older PC, a named agent or a known organization.

- Preserve status such as unverified, testing, supported, rejected or stale.
- Keep sample counts, confidence, evidence/source digest, timestamps and expiry.
- Separate contributor identity from validation/reviewer identity.
- Deduplicate records and handle schema/version conflicts explicitly.
- Do not silently replace a well-supported artifact with a newer but weaker one.
- Receiving organizations may independently validate or reject imported artifacts without falsifying the origin's status.
- Imported learning is research input, not an order, command or execution authorization.

## 6. Synchronization and outage behavior

Organization-internal memory and cross-organization memory must have separate synchronization paths and cursors.

- Local modules communicate through the local runtime and local memory API.
- Multi-PC replication within one organization uses authenticated peer transport and organization-scoped authorization.
- Cross-organization learning uses a separate authenticated API and explicit publication/subscription policy.
- If the cross-organization service is unavailable, local research and internal memory continue. Eligible artifacts may be queued durably for later synchronization, subject to expiry and revocation checks.
- Reconnection deduplicates stable artifact/event IDs, validates schema and provenance, reconciles versions and never blindly replays side effects.
- Cross-organization synchronization never transfers CEO leadership, organization membership, execution permissions or private account state.
- Shared-learning outage must not trigger network attempts between modules on the same PC.

## 7. UI and audit

The cockpit/office must label records distinctly as "Internal — organization memory" or "Shared — cross-organization learning". Show origin organization, agent, department, installation, contribution time, validation status, confidence/sample size, source lineage and stale/revoked state. Provide filters by organization, contributor, department, status and date. Never expose secrets or private operational fields.

Audit enrollment, identity/name collisions, publication approval/rejection, import, validation changes, revocation, expiry and synchronization errors. Distinguish original contributor from later validators and authors of derived artifacts.

## 8. Required tests and implementation order

1. Local departments share organization memory without network calls.
2. Two organizations retain separate CEO identities, local memory and authorization.
3. Cross-organization sharing exports only eligible allow-listed artifacts.
4. Secrets, account data and organization-private fields are rejected or omitted.
5. Imported artifacts retain verifiable organization/installation/agent provenance.
6. Derived artifacts preserve source lineage and identify the new contributor.
7. Duplicate display names cannot collide or impersonate an existing agent.
8. An installation cannot claim an organization by display name alone.
9. New installations can import approved learning and later contribute their own eligible findings.
10. Cross-organization service outage does not break local memory or local module messaging.
11. Reconnection respects deduplication, expiry, revocation and version conflicts.
12. Shared learning never grants leadership or execution authority.
13. All tests remain PAPER/read-only and create no live side effects.

Implementation order: audit current enrollment/auth/database/API contracts; define immutable identity and provenance schemas; add organization-scoped storage and policy; add cross-organization artifact envelope and validation; integrate the registry; add UI/audit attribution; then test multi-installation behavior. Do not claim end-to-end cross-organization sharing or globally unique agent registration until integration tests pass.
