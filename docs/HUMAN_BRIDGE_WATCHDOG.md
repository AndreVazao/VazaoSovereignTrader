# Human Bridge Watchdog

The watchdog is a control-plane safety layer for the PC browser <-> Android human bridge.

It tracks:
- PC heartbeat: refreshed on authenticated control-plane traffic;
- Android heartbeat: refreshed by the mobile cockpit;
- normal request TTL expiry;
- requests stuck in RESPONDED without being applied.

When a heartbeat is stale, the watchdog reports safe_state=true. It does not submit orders, solve CAPTCHA/2FA, or bypass the Risk Engine. A stale bridge is isolated from trading execution rather than being allowed to fabricate or replay a human action.

Secrets remain RAM-only. Request metadata is durable; passwords, OTPs and response values are not written to disk.

Endpoints:
- POST /human-interaction/heartbeat with source mobile or pc;
- GET /human-interaction/watchdog.

Recommended lifecycle:

PC browser -> Human Bridge -> Android heartbeat -> human response -> PC browser -> APPLIED -> COMPLETED.