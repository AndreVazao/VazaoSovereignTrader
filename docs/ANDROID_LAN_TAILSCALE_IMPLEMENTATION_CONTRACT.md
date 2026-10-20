# Android remote connection: safe next implementation steps

This note is deliberately specific to the current client and backend, based on source inspection of `MOBILE_APP/main.py`, `MOBILE_APP/ui.py`, `PC_ENGINE/api/server.py` and `docs/ANDROID_FIRST_PAIRING.md`.

## Current behaviour verified in source

- Android persists one `pc_url` value in its private `connection.json` file.
- The PC screen exposes one endpoint field; `base_url()` reads that field for all HTTP requests.
- `test_connection()` sends `GET /health` and saves the entered endpoint when it receives HTTP 200.
- Away-from-home Tailscale use is documented, but endpoint discovery and automatic LAN/Tailscale selection are not implemented.
- `/health` is intentionally public health information; private state and commands must still pass the API's token/scope checks. Never treat a successful health probe as proof of authorization.
- The client uses HTTP URLs for LAN/Tailscale examples. Do not use these over untrusted networks; prefer the private Tailscale route and ensure the service/authentication configuration is appropriate.

## Safe implementation contract

1. Replace the single saved endpoint with two explicit fields: `lan_url` and `tailscale_url`. Migrate the legacy `pc_url` into the LAN field only as a user-confirmed/clearly labelled legacy value; do not guess whether an address is LAN or Tailscale.
2. Keep both values local to Android. Never publish a LAN address, token, or endpoint credential to Vercel.
3. For connection checks and idempotent read-only GETs, try the selected LAN endpoint first and the configured Tailscale endpoint second. Record which route authenticated successfully.
4. Do not automatically replay POST requests, uploads, or commands on a different endpoint after timeout/disconnect. The result may be unknown; show that state and reconcile against backend status before any retry.
5. A `/health` response only proves network reachability. Before showing the cockpit as authenticated/ready, require a token-protected private-state request and handle 401/403 distinctly from offline.
6. Keep one authoritative PC engine. Route switching changes only the base URL; it must never start a second engine or duplicate a command.
7. If neither route is reachable, show OFFLINE with manual retry/edit options. No public-IP, port-forward, or Vercel-proxy fallback.
8. Add unit tests for legacy-config migration, LAN success, LAN failure/Tailscale success, both offline, invalid schemes, 401/403 handling, and ensuring POST is never automatically replayed.
9. Validate on a physical Android device, capturing startup logcat and switching between home Wi-Fi and Tailscale. CI build success is not a substitute for these tests.

## Current status

The above is an implementation contract, not a claim that dual-endpoint selection is already present. Current source still uses one `pc_url`; keep the feature marked pending until code and tests land.
