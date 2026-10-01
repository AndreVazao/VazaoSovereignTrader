# Android ADB PAPER local bridge

The Android adapter implements read-only device/emulator observation using the existing transport-neutral execution surface contract.

## What it reports

The adapter returns explicit states rather than guessing that a phone or APK is ready:

- `ADB_UNAVAILABLE`: the ADB executable cannot be resolved or its version command fails.
- `NO_DEVICE`: no device/emulator is connected, or a configured serial is absent.
- `DEVICE_UNAUTHORIZED`: Android has not authorized this computer for ADB.
- `DEVICE_OFFLINE`: ADB reports an offline device.
- `MULTIPLE_DEVICES`: multiple devices are online and no serial was selected.
- `APK_NOT_CONFIGURED`: a device is online, but no Android package name was configured, so app process state was not checked.
- `APP_NOT_OBSERVED`: the configured package process was not observed.
- `APP_OBSERVED`: the configured package process was observed by a read-only ADB command.
- `COMMUNICATION_ERROR`: ADB timed out, returned an error, or produced malformed output.
- `PAPER_INTENT_RECORDED`: a BUY/SELL/CANCEL intent was recorded as metadata only.

## Safety boundaries

- `CONNECT` and `OBSERVE` only refresh ADB/device/app observations. They do not install or launch an APK.
- The adapter never taps controls, types into an app, submits a form, uses accessibility automation, reads credentials/OTPs/cookies, or calls private trading APIs.
- BUY/SELL/CANCEL never invoke ADB and never submit an order. They only record PAPER intent feedback.
- Device serials and raw ADB output are not written to feedback details.
- Feedback is marked PAPER-only, with `orders_submitted=false` and `execution_authorized=false`, and uses the existing bounded local feedback store.
- A healthy ADB connection proves transport visibility only. It does not prove account authentication, exchange connectivity, readiness, profitability or permission to trade.

## Configuration

Construct `AndroidAdbConfig` with:

- `venue_id` (required)
- `adb_path` (optional; otherwise resolve `adb` from PATH)
- `device_serial` (optional; recommended if multiple devices may be attached)
- `package_name` (optional; without it the state is `APK_NOT_CONFIGURED`)
- `command_timeout_seconds` (positive, defaults to 5 seconds)
- `feedback_path` (optional)
- `feedback_max_records` (positive bounded retention, defaults to 2,000)

The bridge does not provision Android SDK/ADB, install drivers, install an APK, enable developer options or authorize a device. Those steps remain explicit local user actions.

## Tests

`tests/test_android_adb_paper_surface.py` covers missing ADB, no device, unauthorized/offline handling, malformed output, timeout, missing package configuration, app process present/absent, multiple devices, request correlation, persistent PAPER feedback and the guarantee that PAPER trade intents do not invoke ADB.
