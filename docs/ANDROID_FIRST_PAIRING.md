# Android first pairing and reconnection

## Status and scope

The USB-assisted setup remains the transport bootstrap. This branch adds a PC-approved, expiring one-time pairing challenge, revocable per-device bearer tokens, restricted device scopes, and Android Keystore-backed token encryption. The Android/Windows hardware flow still requires a real-device validation pass; CI cannot prove OEM-specific Keystore behaviour.

## USB bootstrap on Windows

1. Install Android Platform Tools (ADB) and ensure `adb` is on PATH, or install it under `%LOCALAPPDATA%\Android\Sdk\platform-tools`.
2. On Android, enable Developer options and USB debugging only if you are comfortable granting that access.
3. Connect one unlocked Android device by USB and accept its RSA debugging prompt. Do not accept prompts on an unknown computer.
4. From the repository root, run:

   ```powershell
   .\scripts\pair_android_usb.ps1
   ```

   To install a built APK as part of this assisted step:

   ```powershell
   .\scripts\pair_android_usb.ps1 -ApkPath .\path\to\VazaoSovereignTrader.apk
   ```

5. The helper requires exactly one authorized device and runs `adb reverse tcp:8765 tcp:8765`. In the Android app, use `http://127.0.0.1:8765` and enter the PC's local control token manually.
6. The USB tunnel is temporary. It stops working when the USB/ADB session is removed; it is not a remote-access mechanism.

## Subsequent use

- The APK stores only the PC endpoint in its private app data and retries its existing polling/health calls while running.
- The local control token is deliberately **not** written to the connection configuration. The operator must enter it in the app after a fresh app process until secure Android Keystore storage and one-time device pairing are implemented.
- On the same Wi-Fi, use a reachable PC LAN address and ensure Windows Firewall allows the intended private-network traffic.
- Away from home, install and sign in to Tailscale on both PC and Android, then use the PC's Tailscale address. Do not expose port 8765 directly to the public Internet.
- The endpoint persists, but a successful network connection still depends on the PC service being online, the selected route being reachable, the token being supplied, and the firewall/network policy.

## Security boundaries

- The helper never reads, prints, or stores the local API token.
- USB debugging is an explicit Android user authorization and should be disabled when no longer needed if the operator does not require ADB.
- This helper does not disable Android security controls, bypass login/2FA/CAPTCHA, configure a public port forward, or change PAPER/REAL controls.
- ADB reverse is a temporary bootstrap/diagnostic tunnel, not the final authenticated device-pairing protocol.
- The next milestone is a local one-time pairing challenge with explicit PC approval, a revocable device identity, and secure token storage backed by Android Keystore; then guided LAN/Tailscale selection and connection status.


## Secure device pairing (new)

1. Start the PC service in its usual explicit manner and connect the Android app over USB reverse, LAN, or an already configured private Tailscale network. Never expose port 8765 publicly.
2. In the app, enter the owner token temporarily and press **EMPARELHAR**. The app shows a short confirmation code; the owner token is not saved.
3. At the physical PC console, run:

   ```powershell
   python .\\scripts\\approve_mobile_pairing.py
   ```

   Select the matching device, enter the code shown on the phone, and type `APROVAR`. The request expires after five minutes. Do not approve an unfamiliar device.
4. Return to Android and press **CONCLUIR**. The server issues a random per-device token once. The Android app encrypts it using a non-exportable AES-GCM key in Android Keystore, then clears the owner-token input.
5. A paired device receives only `read_private_state` and `trade_paper` scopes. It cannot use owner-management or REAL-mode scopes. The PC remains authoritative for all risk gates.
6. To revoke a device at the PC console:

   ```powershell
   python .\\scripts\\revoke_mobile_device.py
   ```

   Select the device and type `REVOGAR`. The server stores only a SHA-256 digest of each device token. Revocation blocks subsequent authenticated requests; it does not erase the token from a phone, so also use **ESQUECER** on a device you still control.

### Pairing protocol boundaries

- Creating and completing pairing requires the existing owner token; local PC approval is a separate console action and requires the confirmation code.
- Challenges expire after five minutes and cannot be completed twice. The server persists the token hash, device name, status, scopes, and timestamps; it never persists the raw token or confirmation code.
- The owner token is not stored by the Android app. Device token persistence fails closed if Android Keystore is unavailable; the app attempts to revoke the newly issued token rather than writing plaintext.
- The token is a bearer credential. Use only a trusted local route, USB reverse tunnel, or private overlay network. Do not use plain HTTP across an untrusted network.
- `ESQUECER` removes local token material only. It is not a remote revocation; use the PC helper for server-side revocation.
- The server stores device state in `PC_ENGINE/data/mobile_pairing/mobile_pairing.json` by default. Protect this local file and PC account. Atomic writes are used; last-seen persistence is throttled to once per minute per device.
- The secure-token helper uses the Android Keystore when running in Android. On non-Android hosts it returns failure and never falls back to plaintext.
- Automated tests cover challenge approval, replay rejection, restricted scopes, revocation, and fail-closed storage on non-Android hosts. Physical USB, Android Keystore, and OEM-specific validation remain pending until exercised on a real device.
