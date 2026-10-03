# Private endpoint lease API

Status: implementation in PR #332; not yet deployed or validated on physical devices.

## Trust boundary

The cloud stores short-lived Tailscale routing hints so two approved devices belonging to the same authenticated account can discover each other's private address. A lease is not an identity credential, proof of network reachability, permission to connect, or instruction to the trading engine. The PC agent remains authoritative for execution and risk controls. Clients must independently authenticate the peer; cloud unavailability must not change trading or risk policy.

## Authentication and signed proof

Every request requires `Authorization: Bearer <Supabase access token>`. The account profile must be active and `must_change_password=false`. In addition, each endpoint action must be signed by the registered device private key; the corresponding public key is stored with the approved device.

The body includes a Unix timestamp in milliseconds (within ±120 seconds), a cryptographically random base64url nonce (22–128 characters), and a base64url signature. The signature is over the exact UTF-8 message below, with literal newline separators and no trailing newline:

```text
v1
POST
/api/v1/devices/endpoint
<action: publish or lookup>
<authenticated Supabase user UUID>
<calling device UUID>
<detail: canonical Tailscale address for publish, peer device UUID for lookup>
<timestamp as base-10 integer milliseconds>
<nonce>
```

The server verifies the signature against the calling device's registered public key, checks the account/device ownership and approval state, then atomically inserts a SHA-256 hash of the nonce into a unique database table. Reusing a nonce is rejected. Nonce rows expire logically after ten minutes; scheduled cleanup is an operational follow-up to control table growth. Device-key signing prevents a stolen user session alone from publishing an address, but it does not prove the announced address is reachable or currently assigned to that device.

## Publish or refresh a lease

`POST /api/v1/devices/endpoint`

```json
{
  "action": "publish",
  "device_id": "approved-device-uuid",
  "tailscale_address": "100.100.10.20",
  "timestamp": 1791050000000,
  "nonce": "base64url-random-value-at-least-22-chars",
  "signature": "base64url-device-signature"
}
```

Only an approved device owned by the authenticated user may publish. Accepted addresses are literal Tailscale IPv4 addresses in `100.64.0.0/10` or IPv6 addresses in `fd7a:115c:a1e0::/48`. Public/LAN addresses, hostnames and URL-shaped values are rejected. A successful publish replaces that device's lease and sets expiry to five minutes after server receipt. Client clocks are not trusted except for the bounded freshness check.

## Resolve a peer lease

`POST /api/v1/devices/endpoint`

```json
{
  "action": "lookup",
  "device_id": "calling-approved-device-uuid",
  "peer_device_id": "peer-approved-device-uuid",
  "timestamp": 1791050000000,
  "nonce": "different-base64url-random-value",
  "signature": "base64url-device-signature"
}
```

Both devices must be approved and owned by the authenticated account. Only an unexpired lease for the peer is returned; otherwise `endpoint: null` is returned. Revoked/unapproved peers cannot be resolved even if a lease row remains until expiry or device deletion. GET requests are intentionally not supported for lookup, avoiding signatures and nonce material in query strings and access logs.

## Database and operational requirements

- `202610030001_private_endpoint_leases.sql` creates owner-scoped leases and extends server-side rate-limit scopes.
- `202610030002_endpoint_proof_nonces.sql` creates the replay-protection table.
- These migrations are source only and have NOT been applied to any production Supabase project.
- CI must pass on the exact PR head before merge.
- Add/verify integration tests for cross-account isolation, revoked devices, expired leases, concurrent refresh, rate-limit behavior and nonce replay under concurrent requests.
- Apply migrations only through the approved Supabase migration process after review.
- Test Tailscale reachability and independent peer authentication on real Windows and Android devices.
- When cloud lookup fails or a lease expires, no trading/risk policy changes and no public endpoint fallback is attempted.
- Never expose the PC engine directly to the public internet. Address discovery must not trigger trading actions or change PAPER/REAL mode.
