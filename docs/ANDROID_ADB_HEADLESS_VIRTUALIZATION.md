# Android ADB, headless control and optional phone virtualization

Status: architecture proposal / implementation gate (2026-10-22)

## Goal

Let Sovereign Trader run as a low-resource Windows service while the operator can inspect and manually operate exchange apps that are already on their Android phone. Keep ADB/device control separate from the trading engine and from exchange API credentials. A physical phone is the preferred path for apps tied to the user's existing device/session; a virtual Android device is an optional, on-demand lab, not a prerequisite for 24/7 market-data collection.

## Important distinction: three different capabilities

1. **ADB control of the physical phone** — ADB sends device diagnostics and permitted input/install commands over USB. It does not itself display the phone screen.
2. **Interactive screen mirroring** — scrcpy can display/control a connected Android device while using ADB. Run it only when the operator asks for a visual session; it is not required for the headless Trader service.
3. **Android virtualization/emulation** — Android Emulator runs a separate virtual device on the PC. It does not clone the phone's private app data, authenticated sessions, SIM, hardware-backed keys or identity. Exchange apps may refuse to run or require fresh login on emulators. Never assume that an exchange account/session will transfer from the physical phone.

## Proposed architecture

```text
Windows PC
├─ Sovereign Trader engine + public market-data workers (headless, always on)
├─ Local authenticated control API (loopback by default; private LAN/Tailscale only when configured)
├─ Android Device Bridge service (optional, isolated process)
│  ├─ ADB over USB to the operator's physical Android phone (preferred)
│  ├─ Device state / connection health / explicit operator prompts
│  └─ scrcpy launched on demand, then closed after the visual session
└─ Android Emulator profile (optional, stopped by default; start only for testing)
```

The Android bridge must never become a dependency of market-data collection, risk checks, or the engine's main loop. If ADB, the phone, scrcpy, or the emulator is unavailable, the Trader continues in its existing safe state and the cockpit reports the device as disconnected.

## Resource policy

- Default install: no Android emulator running in the background.
- Keep the Trader engine and public market-data collector independent of the Android bridge.
- Run ADB only when device functionality is enabled; use a single local ADB server and bounded health polling rather than continuous screenshots.
- Launch scrcpy only for a requested interactive session. Close it when the session ends; do not keep video encoding active in the background.
- Start the emulator only on demand for development/testing. Use a single AVD, cold-start only when needed, hardware acceleration when supported, a modest resolution/DPI and capped RAM/CPU in the AVD configuration. Stop it after use.
- Do not prescribe a universal fixed RAM/CPU number until the target PC hardware is known; measure idle and active usage on the actual machine.
- No Android GUI or emulator is required for the core headless service or scheduled Windows startup.

## Security boundaries

- Prefer USB ADB. Do not expose ADB TCP port 5555 to LAN, internet or Tailscale; do not enable wireless debugging persistently as a convenience.
- Pairing/authorization remains an explicit action on the phone. Never silently accept a new ADB host key.
- Do not store exchange passwords, API secrets, session cookies, seed phrases or MFA codes in GitHub, project logs, ADB command lines, screenshots or the Trader's learning memory.
- The bridge may report package presence, device model/Android version, connection state and sanitized diagnostics. It must not scrape app-private storage or extract tokens.
- Exchange login, MFA, CAPTCHA and security confirmations remain manual. Do not bypass app protections, automate withdrawals/transfers, or turn screen interaction into a route around exchange API permissions.
- ADB/UI automation must not submit trades or other financial side effects. Any later controlled action must use the Trader's separately audited server-side authorization, risk and idempotency path—not coordinates or taps on a phone screen.
- A timeout after a potentially mutating interaction means outcome unknown; reconcile manually instead of replaying a tap.
- Device disconnect, USB reconnect, emulator restart or network failover must never change PAPER/REAL mode or grant execution permission.

## Phased implementation and acceptance gates

### Phase A — inventory and diagnostics (no emulator)

- Detect `adb.exe` installation without installing it silently.
- Add a bounded, optional device diagnostic command that reports ADB availability, authorized device count, Android version and connection state, with serials redacted by default.
- Do not run `adb devices -l` output unfiltered into logs because device serials can be identifying.
- Provide explicit operator actions to check connection and open/close scrcpy. Do not start scrcpy on Windows boot.
- Test no-device, unauthorized-device, offline-device, ADB-server failure and device reconnect cases.

### Phase B — physical-phone interaction

- Document USB debugging enablement and revoking authorizations.
- Verify screen mirroring/control with the operator present, manual unlock and manual exchange authentication.
- Verify that the engine and market-data worker remain healthy when the phone is unplugged or ADB is killed.
- Confirm the exchange apps the user needs actually work on the physical phone; the bridge does not need app passwords.

### Phase C — optional Android virtual device

- Use the official Android SDK Emulator and a supported AVD image, only after checking Windows virtualization/hypervisor compatibility and the target PC's resources.
- Keep the AVD stopped by default and clearly label it as a separate test device, not a clone of the user's phone.
- Test whether each required exchange app is available and compatible with that emulator image. If an app blocks emulators, keep that app on the physical phone; do not attempt to evade its checks.
- Measure CPU/RAM while stopped, booting and idle; set practical resource limits based on observed hardware. Verify that stopping the AVD releases resources.
- Never put personal production exchange sessions or credentials in a disposable emulator image.

### Phase D — remote operator cockpit

- Add read-only device status to the PC cockpit/virtual office and APK: connected, authorized, Android version, last check time and sanitized error.
- Show an explicit “Open screen session” action only when the operator requests it; do not stream screenshots continuously.
- Use the existing authenticated private control path; no public inbound ADB or extra public endpoint.
- Require fresh operator confirmation for any action that affects device state; no automated exchange trading through UI taps.

## Definition of done

- Trader and market-data workers start and continue with no phone, no ADB, no scrcpy and no emulator.
- Device health is isolated, bounded, sanitized and visible in the cockpit.
- A physical phone can be connected/disconnected without engine restart or mode change.
- scrcpy is on-demand and terminates cleanly.
- Emulator is optional, stopped by default, and its resource footprint has been measured on the target PC.
- No credentials or app-private tokens are read or stored by the bridge.
- Tests prove that device-control failures cannot authorize or submit an order.
- Physical PC/phone validation is documented separately from CI; no emulator success is presented as proof that the physical exchange apps work.

## Current limitation

This document records the intended design only. It does not claim that ADB, scrcpy or an Android Emulator is installed or working on the user's PC, and it does not claim that the exchange apps support emulators. Validate these items on the target PC and phone before enabling the bridge by default.
