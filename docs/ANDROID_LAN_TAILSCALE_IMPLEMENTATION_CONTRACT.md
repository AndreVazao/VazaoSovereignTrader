# Android remote connection: safe next implementation steps

This note is deliberately specific to the current client and backend, based on source inspection of `MOBILE_APP/main.py`, `MOBILE_APP/ui.py`, `PC_ENGINE/api/server.py` and `docs/ANDROID_FIRST_PAIRING.md`.

## Current behaviour verified in source

- Android now persists separate `lan_url` and `tailscale_url` fields in its private `connection.json` file. Legacy `pc_url` migrates to the LAN field only; the client does not guess which route a legacy address represented.
- The PC screen exposes separate LAN and Tailscale fields. Route candidates are ordered LAN first, then Tailscale, with the last successful route preferred on subsequent requests.
- The request layer may fail over only for GET requests after network/timeout errors. HTTP responses such as 401/403 are returned as definitive responses; POST, PUT, PATCH, DELETE and uploads are never automatically replayed on another route.
- `test_connection()` sends `GET /health`; this proves reachability only, not authentication. The status text explicitly warns that private authorization has not been validated by this probe.
- `/health` is intentionally public health information; private state and commands must still pass the API's token/scope checks. Never treat a successful health probe as proof of authorization.
- The client uses HTTP URLs for LAN/Tailscale examples. Do not use these over untrusted networks; prefer the private Tailscale route and ensure the service/authentication configuration is appropriate.

## Safe implementation contract

1. [x] Replace the single saved endpoint with two explicit fields: `lan_url` and `tailscale_url`. A legacy `pc_url` is migrated into the LAN field for compatibility; it is not guessed to be Tailscale.
2. Keep both values local to Android. Never publish a LAN address, token, or endpoint credential to Vercel.
3. [x] For GET requests, try LAN first and Tailscale second after network-level failure; remember the last route that returned an HTTP response. This is a connectivity route, not proof of authentication.
4. [x] Do not automatically replay POST requests, uploads, or commands on a different endpoint after timeout/disconnect. The result may be unknown; caller must reconcile backend state before any manual retry.
5. A `/health` response only proves network reachability. Before showing the cockpit as authenticated/ready, require a token-protected private-state request and handle 401/403 distinctly from offline.
6. Keep one authoritative PC engine. Route switching changes only the base URL; it must never start a second engine or duplicate a command.
7. If neither route is reachable, show OFFLINE with manual retry/edit options. No public-IP, port-forward, or Vercel-proxy fallback.
8. [ ] Add integration tests for legacy-config migration, mocked LAN success/failover, both offline, 401/403 handling, and proof that POST is not replayed. Current CI tests cover the pure endpoint helpers only.
9. Validate on a physical Android device, capturing startup logcat and switching between home Wi-Fi and Tailscale. CI build success is not a substitute for these tests.

## Current status — 2026-10-20

- Dual endpoint fields and GET-only network failover are implemented in the Android client on PR #388.
- The current test suite validates endpoint normalization/order and the GET-only failover policy. The Android workflow's endpoint unit-test step and debug APK build both passed on run 45: https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/39419467665.
- Still pending: dedicated mocked tests of the actual `_request` method and legacy config migration; authenticated private-state probe (because `/health` is public); physical-device startup/logcat validation; switching between home Wi-Fi and Tailscale on the phone.
- LAN and Tailscale values remain local to Android. No Vercel proxy, public port-forward, or POST failover is introduced.
