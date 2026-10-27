# Android emulator UI smoke tests

The `Android Emulator UI Smoke` GitHub Actions workflow builds a temporary
x86_64 debug APK, starts a hosted Android emulator, installs the APK, and
drives a startup flow with the open-source Maestro CLI.

## What this validates

- Mobile Python contract tests and syntax compilation.
- Buildozer can create an emulator-compatible debug APK.
- Android can install and launch the APK in an API 35 emulator.
- The app process remains alive after launch.
- Captured Android logcat has no detected fatal crash signature.
- A screenshot is captured and OCR checks that the initial cockpit prompt
  (`Como posso ajudar?`) is actually rendered on screen.
- Screenshot, OCR output and logcat are uploaded as the
  `vst-android-emulator-smoke` workflow artifact, including on failure.

## Deliberate boundaries

- The x86_64 APK is a temporary CI test build. The existing release APK workflow
  remains the ARM64 build for physical Android devices; the emulator APK is not
  published as a release artifact.
- This is a UI startup smoke test, not exhaustive navigation, pairing, voice,
  file picker, connectivity, performance, battery, or hardware validation.
- No exchange credentials or live trading are used. The test does not connect
  to a PC engine or exchange and does not submit orders.
- GitHub Actions hosted Linux runners support hardware-accelerated Android
  emulation through KVM. A Windows-hosted runner already runs Windows natively
  for the EXE/install smoke tests; nested guest Windows virtualization is not
  added because it is unnecessary for validating the Windows package on the
  supported runner.
- Maestro CLI is used locally inside GitHub Actions. Maestro Cloud is not used,
  so this workflow does not require a Maestro Cloud account or API token.

## How to run

- On a pull request that changes `MOBILE_APP/**`, `.maestro/**`, or this
  workflow, GitHub Actions runs the emulator smoke test.
- It can also be started manually with `workflow_dispatch`.
- Open the `Android Emulator UI Smoke` run and download
  `vst-android-emulator-smoke` to inspect the screenshot, OCR output and logcat.

A passing run proves that this specific debug build launched and rendered the
startup prompt in the configured virtual device. It does not prove every feature
works on all Android versions or physical devices.