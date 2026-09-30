# Execution surface adapter contract

The execution layer exposes one transport contract for venues that do not share the same interface:
- WEB_BROWSER: browser automation/session.
- DESKTOP_APP: installed desktop application/local bridge.
- ANDROID_APK: Android application through an explicitly configured device/emulator bridge.

Adapters exchange actions and feedback, not authorization decisions.
Every feedback record carries a request id, venue, surface, state, acknowledgement and observation timestamp. Failures must be explicit and machine-readable; silent success is not accepted.
Every action entering this contract is forced to paper_only=True. Real execution authorization remains outside the adapter and continues to be governed by the existing readiness/preflight, reconciliation, Risk Engine and RealModeGuard controls.
For Android, the eventual implementation may use a local ADB/emulator bridge or another supported automation mechanism. Headless mode is acceptable only when the bridge can return deterministic feedback. Credentials, OTPs and session secrets must not be persisted in source or evidence artifacts.
This contract deliberately does not implement a concrete browser, desktop or Android adapter yet. Concrete adapters will be added separately after transport-specific validation and PAPER tests.