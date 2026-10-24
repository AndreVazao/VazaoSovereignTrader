# VST brand identity and asset integration

## Canonical brand

- Product name: Vazão Sovereign Trader (VST).
- Existing vector emblem: `assets/branding/vst-logo.svg`.
- User-supplied raster artwork: `assets/branding/vst-approved-artwork.jpg` (canonical path; original source remains at repository root as `1792476724975.jpg`).
- Android package copy: `MOBILE_APP/vst-approved-artwork.jpg`, kept byte-identical to the canonical raster.
- Android launcher asset: `MOBILE_APP/vst-launcher-icon.png`, generated from the approved artwork by `MOBILE_APP/prepare_brand_assets.py` using Pillow.
- The cockpit prototype uses the vector emblem in the upper-left brand slot and as its SVG favicon.
- Keep the same visual identity across the PC engine launcher, mobile APK, and digital-office executable. Runtime and trading logic must not depend on UI assets.

## Required distribution integration

1. **Windows Trader executable:** generate a Windows `.ico` from the approved source artwork and configure the PyInstaller/packaging icon option for `VazaoSovereignTrader.exe`.
2. **Digital office executable:** use the same `.ico` and show the emblem in the office shell header. Keep the office renderer optional and isolated from the headless engine.
3. **Android APK:** Buildozer is configured to use the generated 512x512 PNG launcher icon. CI installs Pillow and prepares/validates the icon before building. Adaptive-icon safe zones and launcher cropping still require physical-device verification.
4. **Office interior:** add the emblem as the company wall plaque in the CEO room, with sufficient contrast and realistic scale; do not obscure navigation or department labels.
5. **Quality gates:** build both Windows executables and APK, inspect packaged assets, run desktop smoke tests, and test launcher cropping/startup on a physical Android device.

## Asset provenance and current limitation

The repository contains both the hand-authored vector emblem and the user's raster artwork as distinct assets. The virtual-office web prototype uses the raster as its background; the Android cockpit displays the raster above the VST wordmark when the asset exists. The Android build pipeline now generates a PNG launcher icon from the approved image before invoking Buildozer. CI success proves the pipeline passed, but not that the launcher was visually verified on a physical device. Windows `.ico` resources and installer integration remain outstanding.

## Acceptance checklist

- [x] Approved raster artwork committed to `assets/branding/vst-approved-artwork.jpg`; source retained at repository root.
- [ ] Windows icon generated from the approved artwork; both Trader and digital-office executables show it in Explorer/taskbar.
- [x] Android build configured to generate and package a PNG launcher icon from approved artwork.
- [ ] Verify Android launcher cropping/startup on a physical device; adaptive icon support may need a separate pass.
- [x] Android cockpit shows approved artwork in its sidebar; virtual-office web scene uses it as the background.
- [ ] Add artwork as the company wall plaque in the CEO room.
- [ ] Packaging/CI verifies assets exist and are included in each distributable.
- [x] Branding changes do not alter execution mode, exchange permissions, or trading risk controls.
