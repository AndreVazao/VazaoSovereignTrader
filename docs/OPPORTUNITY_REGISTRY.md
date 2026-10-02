# Opportunity Registry — Schema and Safety Contract

## Purpose

`PC_ENGINE/opportunity/registry.py` defines a typed, append-only local evidence registry for opportunities discovered across exchanges and other authorized platforms. It is metadata and evidence only: it is not an order, transfer, subscription, reward-claim or bot-activation interface.

## Record fields

Each `OpportunityRecord` captures:
- stable `opportunity_id`, `venue_id`, and `account_scope`;
- typed category (native automation, copy trading, reward/promotion, fee reduction, research/data, other);
- HTTPS `source_url`, discovery timestamp and source-capture timestamp;
- status, optional expiry, eligibility evidence;
- optional gross and net estimates, itemized non-negative estimated costs;
- required permission names, risk notes, rationale and last-update timestamp;
- hard safety invariants: `paper_only=true` and `execution_authorized=false`.

Source timestamps and provenance are mandatory. HTTPS URLs with embedded username/password are rejected. Materially future timestamps, non-finite financial estimates, negative/non-finite cost values, missing eligibility evidence for confirmed eligibility, and a non-positive estimate for `NET_VALUE_POSITIVE_ESTIMATE` are rejected.

## State semantics

- `DISCOVERED`: identified but not verified.
- `ELIGIBILITY_UNKNOWN`: account/region eligibility remains unknown.
- `ELIGIBLE_CONFIRMED`: current evidence supports eligibility.
- `NET_VALUE_POSITIVE_ESTIMATE`: positive estimate only; not a guarantee.
- `PAPER_TESTED`: tested without real funds.
- `READY_FOR_EXPLICIT_APPROVAL`: review candidate only; no action is performed.
- `CLAIMED_OR_ENABLED_CONFIRMED`: authoritative evidence says the external action occurred; the registry does not perform it.
- `EXPIRED`, `BLOCKED`, `UNSUPPORTED`, `REJECTED_BY_POLICY`, `UNKNOWN_OUTCOME`: explicit terminal or uncertainty states.

New registry records must begin in `DISCOVERED`; direct insertion into a later state is rejected. Transitions are validated against an allowlist. Expired records cannot be promoted to an active state. Discovery cannot authorize execution; setting `execution_authorized=true` or `paper_only=false` is rejected. The registry deliberately has no execution-adapter dependency.

## Persistence

The registry appends JSON Lines records. The latest valid record per opportunity ID is the current snapshot; malformed rows are skipped so one damaged line does not hide later valid records. Repeating an identical write is idempotent. Updating an existing record without a valid state transition is rejected. A status transition appends a new record rather than overwriting historical evidence.

The JSONL store is local evidence, not a secure credential store. Do not include secrets, API keys, passwords, session tokens, private balances or unredacted sensitive account data in fields.

## Current limitations

- Official-source ingestion, URL allowlisting, source hashing, automated expiry sweeps, account eligibility checks, dashboard wiring and platform adapters are not implemented by this module.
- A status value is only as trustworthy as the evidence supplied by its caller; future ingestion code must attach authoritative source and observation metadata.
- This model does not authorize REAL and must remain separate from readiness, preflight, Risk Engine, RealModeGuard, operator approval and reconciliation.
- A future implementation must add tests before connecting any account-specific source or UI.
