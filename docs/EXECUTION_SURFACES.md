# Execution surfaces

The trader is designed to observe and, only after the existing execution gates authorize it, interact with a venue through the surface actually available on that venue.

Supported surface categories:

- **API** — native/private API when a supported adapter exists.
- **WEB_BROWSER** — Playwright-managed web session with a persistent per-platform profile.
- **DESKTOP_APP** — installed Windows or other desktop trading application; future adapters may use an explicitly configured local automation/bridge.
- **ANDROID_APK** — an installed Android application, accessed through an explicitly configured emulator/device bridge (for example ADB) or another supported local automation layer.
- **HUMAN** — explicit human interaction through the existing Human Interaction Bridge when login, 2FA/OTP, CAPTCHA or another interaction cannot be automated.

The operational health layer classifies the transport itself as HEALTHY, DEGRADED, DOWN or NOT_CONFIGURED. It must not infer profitability, OOS quality, risk approval or execution authorization from transport health.

Android and desktop automation are deliberately represented as execution surfaces even when the implementation is not yet available for a particular venue. The architecture therefore does not assume that every exchange must expose an API.

## Android / emulator direction

For APK-only venues, the intended future flow is:

PC trader -> local Android/emulator bridge -> APK UI -> observed result/feedback -> local evidence

The bridge must provide deterministic feedback (connection state, application state, action acknowledgement and failure reason) and a bounded evidence trail. Headless operation is acceptable where the emulator/automation stack supports it reliably.

No APK adapter should persist passwords, OTPs or session secrets in repository artifacts. Human verification remains manual; CAPTCHA/anti-bot mechanisms are not bypassed.

All transport integrations remain PAPER-first and must pass the existing Risk Engine, readiness/preflight/reconciliation and RealModeGuard controls before any future REAL consideration.
