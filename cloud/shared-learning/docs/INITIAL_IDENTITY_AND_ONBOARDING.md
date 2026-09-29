# Initial identity and secure onboarding plan

## Reserved initial usernames

These are reserved identity names, not live accounts:
- `AndreVazao` — display name `André Vazão`; intended global administrator.
- `DiogoRocha` — display name `Diogo Rocha`; intended standard member.

No password, password hash, recovery code, token, or secret belongs in source control. The previously discussed temporary password must be supplied through a one-time trusted provisioning operation after the Supabase project exists; it must never be embedded in a migration, environment example, installer, or Git history. Both accounts must be forced to replace any temporary credential before normal use. Because `123456` is weak, the production provisioning flow should require rate limits, short-lived setup access, and immediate rotation; do not enable these accounts until this is implemented.

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
6. Register each device as pending and approve it independently.
7. Deliver only authorized, signed configuration and public aggregate learning artifacts. Keep local risk gates authoritative.
8. Test invalid sessions, username collision, role escalation, device revocation, cross-user access, audit redaction, vault ciphertext-only storage, and rollback before rollout.

## Current implementation boundary

This branch adds the data model and reservation of the two usernames only. It does not create Supabase users, store passwords, deploy infrastructure, enable cloud sync, or authorize live trading. The API workflows for provisioning, device approval, signed configuration and encrypted vault operations must be implemented and tested before production onboarding.
