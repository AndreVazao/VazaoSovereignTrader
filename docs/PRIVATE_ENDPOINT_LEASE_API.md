# Private endpoint lease API

Status: implementation in PR #332; not yet a deployed or device-validated feature.

## Purpose and trust boundary

The cloud service stores short-lived Tailscale routing hints so two approved devices belonging to the same authenticated account can discover each other's current private address. The lease is not an identity credential, proof of device possession, permission to connect, or instruction to the trading engine. Clients must independently authenticate the peer and enforce local policy. The PC agent remains authoritative for execution and risk controls; local operation must not depend on cloud availability.

## API

All requests require `Authorization: Bearer <Supabase access token>`. Account profile must be active and the password-change requirement cleared. Responses use `Cache-Control: no-store`.

### Publish or refresh

`POST /api/v1/devices/endpoint`

Body (strict allow-list):
```json
{
  "device_id": "approved-device-uuid",
  "tailscale_address": "100.100.10.20"
}
```

Only an approved device owned by the authenticated user may publish. Accepted addresses are literal Tailscale IPv4 addresses in `100.64.0.0/10` or IPv6 addresses in `fd7a:115c:a1e0::/48`. Public/LAN addresses, hostnames and URL-shaped values are rejected. A successful publish replaces that device's lease and sets expiry to five minutes after server receipt. Client clocks are not trusted.

### Resolve a peer

`GET /api/v1/devices/endpoint?device_id=<own-uuid>&peer_device_id=<peer-uuid>`

Both devices must be approved and owned by the authenticated account. Only an unexpired lease for the peer is returned; otherwise `endpoint: null` is returned. Revoked/unapproved peers are not resolvable even if an old lease row remains until expiry or device deletion.

## Operational requirements and remaining acceptance work

- Apply the migration `202610030001_private_endpoint_leases.sql` only through the approved Supabase migration process after review; this PR does not apply production migrations.
- CI must pass on the exact PR head before merge.
- Add/verify integration tests for cross-account isolation, revoked devices, expired leases, invalid address rejection, rate-limit behavior and simultaneous refreshes.
- Connect Windows and Android clients only after defining a signed, replay-resistant request proof for publishing. The current route authenticates the account bearer token and checks ownership/approval; it does not itself require a per-request device-key signature. Do not treat this as sufficient proof that the announced address belongs to the physical device.
- Test Tailscale reachability and independent peer authentication on real Windows and Android devices.
- Confirm offline fallback: when cloud lookup fails or the lease expires, no trading or risk policy changes and no public endpoint fallback is attempted.
- Never expose the PC engine directly to the public internet. Address discovery must not trigger trading actions or change PAPER/REAL mode.
