# Execution surface dashboard catalogue

The local dashboard now exposes `/execution-surfaces`.

The endpoint is deliberately configuration-only at this stage:
- it identifies configured venue/surface pairs;
- it distinguishes NOT_CONFIGURED from configured-but-not-yet-probed;
- it reports whether the entry came from configuration;
- it explicitly marks live_probe=false until a persistent health/feedback store is wired.

Supported surface vocabulary:
- WEB_BROWSER
- DESKTOP_APP
- ANDROID_APK
- HUMAN

This endpoint never probes, clicks, submits orders or changes execution authorization. All records remain PAPER-only.

The dashboard keeps this operational layer separate from:
- venue economic evidence;
- OOS/walk-forward uncertainty;
- Risk/readiness;
- REAL authorization.

The next evolution is to feed the catalogue with the already-defined ExecutionSurfaceStatus snapshots and adapter feedback so the dashboard can show live connection state, last feedback age, reconnects and write health without conflating transport health with trading quality.
