# Android first pairing and reconnection

## Status and scope

This is the first safe increment of the USB-assisted setup. It installs the APK optionally and creates an ADB reverse tunnel for initial local verification. It does **not** yet implement cryptographic device pairing, automatic Tailscale installation, or Android Keystore-backed token storage. Those remain explicit follow-up work and must not be described as completed.

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
