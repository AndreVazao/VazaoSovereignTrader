# Shared Intelligence Privacy and Network Boundaries

## Purpose

Each trader instance belongs to one owner and keeps its financial and execution state private. Instances may exchange only approved, aggregated learning artifacts through the shared-intelligence service.

## Network model: Tailscale is not the learning database

- Tailscale provides private network connectivity and device identity for the owner's PC and phone.
- A tailnet is an administrative/network trust boundary. Devices in one tailnet must not be assumed isolated from one another unless access controls enforce that isolation.
- Shared learning should travel through the authenticated HTTPS shared-intelligence API, not by exposing one owner's local ledger or data directory to another owner's devices.
- The phone should connect only to its owner's PC/API. Other owners' PCs and phones must not be reachable unless an explicit, separately reviewed operational need exists.
- A common tailnet can be used only with restrictive grants/ACLs that allow each phone to reach only its assigned PC/API and deny peer-to-peer access by default. Separate tailnets per owner are a simpler isolation boundary where practical. A shared learning service does not require all participants to be in one tailnet.

## Data that may be shared

Only a versioned, allow-listed, aggregated artifact such as strategy identifier, market/regime, horizon, sample count, win rate, and net performance statistics after estimated costs. Shared artifacts are advisory inputs for research/learning only.

## Data that must remain private

- Exchange API keys, tokens, passwords, and authentication material.
- Balances, equity, deposits/withdrawals, and account identifiers.
- Individual orders, fills, positions, trade histories, and personal ledger rows.
- Owner-specific logs, device identifiers, and raw market/account snapshots that could reveal a participant's activity.
- Any source references that can identify an owner or device. Provenance should use opaque, non-reversible references and must not embed names, emails, account IDs, device names, or paths.

## Required controls before enabling multi-user cloud sharing

1. Authenticate every push and pull; derive tenant identity server-side, never trust a client-supplied owner field.
2. Validate the allow-list on both client and server. Reject unknown fields and oversized or malformed values.
3. Apply per-tenant rate limits and quotas, enforce payload size limits, and paginate bounded results.
4. Never expose raw private state through shared-learning endpoints, logs, errors, or analytics.
5. Prevent one tenant from listing or deleting another tenant's private data. Shared artifacts are the only cross-tenant surface.
6. Treat imported artifacts as untrusted advice: validate schema, freshness, expiry, provenance, and statistical eligibility. They must never directly authorize orders or REAL mode.
7. Use TLS, secret storage, secret rotation, and least-privilege service credentials. Do not put secrets in the repository or client APK.
8. Add integration tests for cross-tenant isolation, unauthenticated access, spoofed owner IDs, unknown/private fields, stale artifacts, and cloud outage behavior.
9. Keep cloud sync optional and fail-safe: local PAPER research must continue if the service is unavailable; a sync failure must never enable execution.
10. Before real-money use, review the deployed Vercel service and its database access policies separately. Client-side validation alone is not a privacy boundary.

## Current implementation status

The PC repository contains a local allow-listed artifact model, integrity checks, an importer, and a provider contract for the Vercel API. This does not by itself prove the deployed Vercel service has tenant isolation or that cloud sharing is operational. Those properties must be verified in the actual Vercel project and its database policies before enabling sharing.

The default rollout should be: isolated local PAPER mode first; verify owner-private paths and identity; verify Vercel tenant isolation; run synthetic multi-tenant tests; then enable advisory sharing. Shared learning must not bypass local readiness, risk, reconciliation, or REAL-mode guards.
