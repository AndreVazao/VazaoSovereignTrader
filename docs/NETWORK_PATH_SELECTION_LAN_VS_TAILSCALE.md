# LAN at home, Tailscale away from home

## Required client behaviour

- At home, prefer the backend's explicitly configured private LAN URL.
- Away from home, use the backend's Tailscale IP/hostname and port.
- Vercel is an account-scoped rendezvous/discovery service only. It must not proxy backend API traffic, commands, or orders.
- The same PC backend remains authoritative. Changing network paths must not start another engine or create separate state.

## Safe path selection

1. Keep separate local settings for the LAN endpoint and the Tailscale endpoint; do not upload LAN addresses to Vercel.
2. Probe the configured LAN endpoint first. Use it only after a successful health response and authenticated API request.
3. If LAN is unreachable, probe the configured Tailscale endpoint. Do not infer that the phone is away from home solely from a failed probe.
4. If neither endpoint works, show offline and let the operator retry or correct the endpoint. Never fall back to a public IP, open port, or Vercel proxy.
5. Save successful endpoint choice locally, but re-check reachability on reconnect. A timeout on a command is an unknown outcome until backend state is reconciled.
6. Keep backend API authentication and per-device scopes mandatory on both LAN and Tailscale. Tailscale membership alone is not API authorization.
7. Do not assume a Tailscale endpoint exists or that Vercel can create a Tailscale tunnel. Tailscale must be installed/configured on the PC and phone; remote discovery must publish only the private Tailscale endpoint with expiry/revocation.

## Validation checklist

- LAN success selects LAN while at home.
- LAN failure followed by Tailscale success selects Tailscale.
- Both failures produce an explicit offline state, without public fallback.
- Expired/revoked device token is rejected on both paths.
- Vercel outage does not break an already configured LAN connection.
- Vercel never receives or relays API commands, orders, credentials, or LAN addresses.
- Network switching does not create a second engine or repeat a command automatically.
- Android real-device startup and logcat validation are performed separately; successful APK compilation is not proof of runtime stability.

## Current implementation boundary

This document records the required behaviour, not a claim that automatic endpoint discovery or path switching has already been implemented. The current Android client stores a single `pc_url`; LAN/Tailscale endpoint selection remains implementation work.