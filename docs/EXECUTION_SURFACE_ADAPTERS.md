# Execution surface adapter contract

The execution layer exposes one transport contract for venues that do not share the same interface:
- WEB_BROWSER: browser automation/session.
- DESKTOP_APP: installed desktop application/local bridge.
- ANDROID_APK: Android application through an explicitly configured device/emulator bridge.

Adapters exchange actions and feedback, not authorization decisions.
Every feedback record carries a request id, venue, surface, state, acknowledgement and observation timestamp. Failures must be explicit and machine-readable; silent success is not accepted.
Every action entering this contract is forced to paper_only=True. Real execution authorization remains outside the adapter and continues to be governed by the existing readiness/preflight, reconciliation, Risk Engine and RealModeGuard controls.
For Android, the eventual implementation may use a local ADB/emulator bridge or another supported automation mechanism. Headless mode is acceptable only when the bridge can return deterministic feedback. Credentials, OTPs and session secrets must not be persisted in source or evidence artifacts.
This contract now has concrete PAPER implementations for browser and desktop surfaces. The browser adapter uses Playwright; the desktop adapter is a Windows-first local subprocess/UI-observation bridge. Both remain PAPER-only and reuse persistent feedback telemetry. Android remains a separate transport-specific implementation using an explicitly configured ADB/emulator/device bridge.