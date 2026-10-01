# Android ADB PAPER bridge

## Purpose

The Android surface adapter observes Android devices and emulators through the local Android Debug Bridge (ADB). It is operational telemetry only. It does not install or launch APKs, tap the UI, read app data, bypass authentication, or submit trading orders.

## Explicit configuration

Add an entry to `execution_surface.platforms` in the local PC configuration. Example:

```json
{
  "execution_surface": {
    "feedback_path": "PC_ENGINE/data/execution/surface_feedback.jsonl",
    "feedback_max_records": 2000,
    "platforms": {
      "android-local": {
        "surface": "ANDROID_APK",
        "adb_path": null,
        "device_serial": null,
        "package_name": "com.vazao.sovereigntrader",
        "command_timeout_seconds": 5.0
      }
    }
  }
}
```

Use the actual package ID built into the APK. Leaving `adb_path` null resolves `adb` from PATH. A configured device serial is recommended when multiple devices/emulators may be connected. Do not commit machine-specific paths or local runtime configuration.

## Explicit lifecycle

The runtime manager is inert on construction and instantiation. No ADB command runs until an operator explicitly invokes the authenticated runtime probe endpoint.

1. Install Android Platform Tools from an official Android SDK distribution and authorize the intended device locally.
2. Configure the adapter in the local, untracked runtime config.
3. Instantiate a runtime using `POST /execution-surfaces/runtime/instantiate` with `surface: ANDROID_APK` and the configured venue ID. This creates an adapter object only.
4. Invoke `POST /execution-surfaces/runtime/probe` for the returned runtime ID to perform read-only ADB observation.
5. Review `GET /execution-surfaces/runtime` and `GET /execution-surfaces`. Runtime health is transport status, not economic evidence or execution authorization.

The adapter uses bounded subprocess timeouts and `shell=False`. It distinguishes ADB unavailable, no device, unauthorized device, offline device, multiple online devices, APK not configured, application process not observed, observed process, malformed output, and communication errors. Only a single selected online device with the configured package process observed reports `APP_OBSERVED`.

## Safety and limitations

- `CONNECT` and `OBSERVE` are read-only ADB probes; they do not install, start, or control the app.
- `BUY`, `SELL`, and `CANCEL` produce a PAPER intent record only. They never invoke ADB.
- Every feedback record remains `paper_only=true`, `orders_submitted=false`, and `execution_authorized=false`.
- Runtime instantiation, probing, automatic restarts, and background polling are not enabled automatically.
- A successful ADB probe does not prove the APK is authenticated, its UI is usable, an exchange works, or a strategy is profitable.
- Automated tests mock ADB subprocesses. Physical Android/emulator and OEM-specific validation remains outstanding until performed on an authorized local device.
