# Install Readiness and Cloud Coordination

Status date: 2026-10-03. This document is an implementation plan, not a claim that production deployment or physical-device validation has happened.

## User-visible completion target

The first useful release is ready when a user can install the Windows package, launch the PC engine in PAPER mode, install the Android APK, pair the phone with the PC, and keep the private connection working after restart. The UI must show clear status and actionable errors rather than claiming a connection that was not verified.

## Intended responsibilities

### PC node
- Owns the engine, local market data, local state, risk controls and any supported platform automation.
- Binds its authenticated local API to a private interface; never requires a public inbound port.
- Continues local PAPER/research operation if Vercel or the internet is unavailable.
- Advertises only connection metadata explicitly approved for discovery. Never advertise secrets, account data, balances, or trading history.

### Android companion
- Generates/holds a device key using platform-appropriate secure storage where supported.
- Requires explicit approval and proof-of-possession before the device is trusted.
- Uses the user's own Tailscale network to reach the PC; validates the selected endpoint and authenticates to the PC API.
- Re-prompts for credentials/tokens when they are intentionally not persisted; revocation must invalidate access.

### Vercel coordination service
- Handles account-scoped device enrollment, approval status, ephemeral endpoint discovery and versioned shared-learning metadata.
- Returns endpoint data only to an authenticated user and their authorized devices; endpoint records are short-lived and revocable.
- Treats endpoint announcements as untrusted input: validate address family/range, reject malformed values, enforce size limits and rate limits, and never turn an announced address into a command to fetch arbitrary URLs.
- Prefer Tailscale IPv4 (100.64.0.0/10) or Tailscale IPv6 (fd7a:115c:a1e0::/48) addresses. Do not publish public IPs by default. IP discovery alone is not proof of identity or authorization.
- Shares only explicitly allow-listed, non-sensitive learning artifacts. Shared learning is advisory and cannot override local risk, readiness, preflight, reconciliation, or PAPER/REAL controls.
- Must not proxy trading commands or become a central trading execution service.

## Discovery protocol requirements

1. A user signs in through the approved authentication flow.
2. PC and phone register device public keys; new devices begin pending.
3. A trusted approval flow checks proof-of-possession and records approval/audit events. A device cannot approve itself.
4. An approved PC publishes its Tailscale address and a short expiry, tied to its owner and device ID. Never trust owner/device IDs supplied without checking them against the authenticated principal and database records.
5. The approved phone retrieves only the current owner's eligible PC endpoint. The response uses no-store caching; no endpoint data in public pages, logs, analytics, or shared learning artifacts.
6. The phone connects over Tailscale and authenticates directly to the PC. A successful cloud lookup must not be displayed as a successful PC connection until the PC responds.
7. Refresh endpoint leases on a bounded interval; remove expired entries; provide manual refresh and a clear offline state.
8. Revoking a device removes its ability to discover endpoints and must also be enforced by the PC API's local authentication/authorization.

## Security and privacy acceptance checks

- Unauthenticated, expired, pending, revoked, or cross-user requests are denied.
- User A cannot read or overwrite user B's endpoint or device records.
- Public IPs, LAN addresses, arbitrary hostnames, URL strings, credentials, and extra JSON fields are rejected unless a separate reviewed design explicitly permits them.
- Only valid Tailscale address ranges are accepted for the first version; addresses are parsed as IP literals, never DNS-resolved or fetched by the cloud.
- Expired leases are not returned. Concurrent updates cannot extend a lease beyond the documented maximum.
- Endpoint response has no-store caching and sensitive fields are excluded from logs and errors.
- Rate limits, audit events, revocation, schema migration rollback and service-down behavior are tested.
- No cloud configuration can change local risk limits, enable REAL mode, submit orders, transfer funds or bypass human approval.

## Install and release gates

### Automated
- Python test suite passes on the exact PR head.
- Windows EXE/installer workflow passes on the exact PR head.
- Shared-learning service tests and production build pass.
- Android APK workflow produces a non-empty artifact and reports its exact commit SHA.
- Dependency/build output is inspected for accidental secrets; no credentials or private runtime data are packaged.
- A documented smoke-test checklist is included with every installable release.

### Manual before calling it install-ready
- Install the Windows package on a clean supported Windows machine and launch it.
- Confirm engine starts in PAPER mode, local API is not publicly exposed, and restart preserves expected local state.
- Install APK on a physical Android phone and confirm permissions, storage, and UI behavior.
- Pair via the supported USB-assisted setup; then test direct Tailscale reconnection without USB.
- Change network / let the endpoint lease expire / restart PC / stop the cloud service; confirm clear status and safe recovery.
- Revoke the phone and verify access is denied by both discovery and PC API.
- Verify logs do not contain tokens, passwords, OTPs, account balances, or private trade history.

## Vercel and infrastructure prerequisites

The repository contains a Next.js service in cloud/shared-learning, but source code is not a deployment. Before production deployment, the owner must choose/confirm the intended Vercel team/project and Supabase organization/region, review pricing and terms, provision infrastructure, apply migrations, configure server-only environment variables, and run preview security tests. Do not deploy to an unrelated Vercel project or commit environment secrets.

## Current known gaps at this handoff

- Cloud service is not confirmed deployed; no live endpoint is known.
- Production Supabase setup and trusted account provisioning are not confirmed complete.
- Physical Android/Windows installation and USB/Tailscale pairing have not been confirmed.
- The APK workflow exists, but artifact success must be verified from a real workflow run.
- Endpoint discovery needs its own reviewed schema, API, tests, lease/expiry semantics and client integration before it can be treated as implemented.
- The PC engine's local maintenance sync must be confirmed wired into lifecycle and tested offline before enabling cloud sync by default.

## Order of execution

1. Establish verified install artifacts and a reproducible smoke-test checklist.
2. Close endpoint discovery API/schema/test gaps with strict owner scoping and short-lived Tailscale-only leases.
3. Integrate endpoint discovery into the PC and Android clients, preserving direct private PC connection.
4. Verify cloud shared-learning service tests, migrations, account/device approval flow and rate limits.
5. Deploy only after explicit infrastructure/cost approval; validate in preview before production.
6. Complete physical-device test matrix and publish installation instructions with checksums and rollback.
7. Keep live execution disabled until separate evidence-backed readiness and risk requirements are met.
