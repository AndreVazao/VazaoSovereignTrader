# Initial identity and secure onboarding plan

## Reserved initial usernames

These are reserved identity names, not live accounts:
- `AndreVazao` — display name `André Vazão`; intended global administrator.
- `DiogoRocha` — display name `Diogo Rocha`; intended standard member.

No password, password hash, recovery code, token, or secret belongs in source control. The previously discussed temporary password must be supplied through a one-time trusted provisioning operation after the Supabase project exists; it must never be embedded in a migration, environment example, installer, or Git history. Both accounts must be forced to replace any temporary credential before normal use. The initial credential is weak and must only be used for a tightly rate-limited bootstrap step with immediate rotation; do not enable these accounts until this is implemented.

## Trust boundaries

- Supabase Auth validates credentials and issues sessions. Server routes validate tokens with Supabase Auth; username or role supplied by a client is never authoritative.
- A reserved username does not grant a role. Only a trusted server-side provisioning operation may consume a reservation, create the profile, and assign the predeclared role. Enforce that only the single initial admin identity can be promoted to `admin`; later admin changes require an audited, explicit owner-authorized operation.
- Device registrations start as `pending`; each device requires a distinct approval and can be revoked independently.
- The cloud vault stores ciphertext only. Encryption/decryption keys are client-side; loss of the recovery key may mean loss of recoverability. Never store exchange API secrets in the ordinary vault without a separate stronger design.
- Configuration is versioned and signed, with separate draft/approval/activation/rollback states. A delivered config is untrusted until signature and schema validation succeed locally. It must not alter local hard risk limits, exchange credentials, or PAPER/REAL authorization.
- Audit records contain minimal metadata, never passwords, access tokens, recovery keys, private trade history, balances, or order payloads.

## First-access sequence

1. Owner creates the cloud resources only after region, cost, and organization are confirmed.
2. Configure Supabase Auth and server-only Vercel environment variables.
3. Run the database migrations and verify RLS/service-role boundaries.
4. Provision the two reserved usernames through a trusted one-time workflow, not SQL containing passwords.
5. Require credential rotation before granting ordinary access; require MFA/owner approval for privileged administration where supported.
6. Register each device as pending, require a short-lived one-time signed proof-of-possession challenge, then approve only through an active admin account; the approval transaction rechecks eligibility and records an audit event.
7. Deliver only authorized, signed configuration and public aggregate learning artifacts. Keep local risk gates authoritative.
8. Test invalid sessions, username collision, role escalation, device revocation, cross-user access, audit redaction, vault ciphertext-only storage, and rollback before rollout.

## Device security endpoint protections

Device registration, challenge issuance, proof verification and administrator approval use database-backed per-account fixed-window limits. Current limits are 10 registrations / 5 minutes, 10 challenges / 5 minutes, 8 proof attempts / 5 minutes, and 20 approval attempts / 5 minutes. Rate-limit storage and incrementing are atomic in PostgreSQL; if the limiter RPC fails, the routes fail closed with a service error. A limit breach returns HTTP 429.

An administrator cannot approve a device registered to their own account. Approval remains restricted to an active admin account whose mandatory password-rotation flag is cleared, and the database function independently checks role/account state and possession proof before writing the approval and audit event in one transaction.

These controls are a baseline, not complete abuse monitoring: production still needs edge/WAF controls, alerting, MFA/step-up verification, migration/RPC validation and integration tests against a disposable Supabase project. Rate limits are per authenticated account and are not a substitute for network-level abuse controls.

## Current implementation boundary

The repository contains identity/device/config/vault schema foundations, reserved usernames, authenticated owner-scoped vault ciphertext routes, and (on the device-proof feature branch) one-time challenge, signature verification and audited admin-approval foundations. Device registration alone never approves a device. The new flow still needs CI/security review, integration tests, rate limiting/abuse monitoring and validation against a real disposable Supabase preview before production use. Trusted account provisioning/login, mandatory rotation enforcement end-to-end, MFA/owner recovery, signed configuration approval/rollback, and complete desktop/mobile vault restore are not complete. No Supabase users are provisioned, no infrastructure is deployed, cloud sync remains disabled by default, and no live trading is authorized.
