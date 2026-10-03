# Private endpoint client integration contract

## Purpose

This document defines the next implementation boundary for publishing and discovering a PC/Android device's private Tailscale endpoint through the Shared Learning Service. It records the current client/server compatibility gap so client code is not wired to the wrong identity system.

## Verified current state

- The cloud endpoint `POST /api/v1/devices/endpoint` requires a Supabase Auth access token in `Authorization: Bearer ...`.
- The request body includes an approved cloud `device_id`, action-specific data, a timestamp, a random nonce and a signature made by the private key corresponding to `authorized_devices.device_public_key`.
- Cloud device registration currently accepts a public key and label, creates a `pending` device, then uses the challenge/verify/proof-of-possession flow and a separate admin approval before the endpoint route accepts the device.
- The existing Android cockpit is primarily paired to the local PC API using a local owner token/per-device bearer token. Its current local pairing store and scopes are not the same identity system as Supabase Auth and `authorized_devices`.
- Therefore, the existing local pairing token must not be sent to the cloud endpoint as if it were a Supabase access token, and the local PC device ID must not be assumed to be a cloud `authorized_devices.id`.

## Required design before client integration

1. **Explicit cloud account session.** Decide how an owner signs into the Shared Learning Service from the trusted setup flow. Use Supabase Auth access tokens only for cloud routes; never reuse the local PC control token.
2. **Independent device keypair.** Generate a per-install keypair on each client. Keep the private key non-exportable where platform APIs allow it (Android Keystore; Windows CNG/DPAPI-backed protected storage as appropriate). Never upload the private key, put it in logs, or include it in backups/shared-learning artifacts.
3. **Cloud device enrollment.** Submit the public key to the existing registration route, obtain a cloud challenge, sign the challenge locally, verify proof-of-possession, and wait for explicit administrator approval. Store the returned cloud device UUID separately from the local PC pairing identity.
4. **Canonical endpoint proof.** Both clients must sign exactly the canonical UTF-8 message specified in `docs/PRIVATE_ENDPOINT_LEASE_API.md`. Timestamp is Unix milliseconds; nonce is cryptographically random base64url; signatures use the registered key and must be canonical base64url. Do not hand-roll different newline/order/encoding rules per client.
5. **Address publication.** Publish only a literal address from the authenticated private Tailscale interface. Validate the interface/address locally and let the cloud parser reject anything outside Tailscale's CGNAT IPv4 or ULA IPv6 ranges. Do not publish public IPs, LAN addresses, hostnames, URLs, ports or credentials.
6. **Peer lookup and connection.** Lookup returns routing metadata only. Before any local API request, independently authenticate the peer connection using the existing PC-side authentication and device authorization. An endpoint lease or signature is not a transport credential.
7. **Lease lifecycle.** Refresh before the five-minute lease expires, tolerate cloud unavailability without blocking local operation, stop publishing on logout/revocation/Tailscale disconnect, and clear local cached endpoint metadata on expiry or device revocation.
8. **No authority escalation.** Cloud discovery must never change the local engine's risk policy, preflight, PAPER/REAL mode, execution authorization or owner-controlled settings. No orders, transfers or exchange credentials pass through this service.

## Required integration tests

- Owner A cannot publish for, look up, or learn Owner B's device or lease.
- Pending and revoked devices cannot publish or look up.
- An invalid signature, altered canonical field, stale timestamp, malformed nonce, repeated nonce and concurrent replay are rejected.
- A lease is invisible after expiry and refresh replaces only the same owner's lease for that device.
- Non-Tailscale IPv4/IPv6, hostname, URL-shaped input and malformed address are rejected.
- Client private keys never appear in HTTP payloads, logs, files, crash reports or shared artifacts.
- Cloud outage, invalid response and lease expiry do not disable the local PC engine or relax risk controls.
- A discovered peer still fails closed unless its independent local authentication succeeds.

## Rollout gates

- Keep migrations as reviewed source until the approved Supabase migration process is confirmed.
- Do not claim the feature is ready until client signing, account enrollment, integration tests and real Windows/Android tests are complete.
- Do not expose the PC API publicly; use the private Tailscale network.
- PAPER/read-only defaults and all existing REAL-mode gates remain unchanged.
