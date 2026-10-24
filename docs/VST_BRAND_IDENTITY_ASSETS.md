# VST brand identity and asset integration

## Canonical brand

- Product name: Vazão Sovereign Trader (VST).
- Existing vector emblem: `assets/branding/vst-logo.svg`.
- User-supplied raster artwork: `assets/branding/vst-approved-artwork.jpg` (canonical path; original source remains at repository root as `1792476724975.jpg`).
- Android package copy: `MOBILE_APP/vst-approved-artwork.jpg`, kept byte-identical to the canonical raster.
- Android launcher asset: `MOBILE_APP/vst-launcher-icon.png`, generated from approved artwork by `MOBILE_APP/prepare_brand_assets.py`.
- Windows icon: `assets/branding/vst-approved-artwork.ico`, generated from the canonical raster by `scripts/prepare_windows_brand_icon.py`.
- Cockpit prototype uses the SVG emblem in the header and as its favicon; the virtual-office scene uses the supplied raster artwork as a background.
- Runtime and trading logic must not depend on UI assets.

## Packaging integration

1. **Windows PC engine and market-data collector:** the installer build installs Pillow, generates the ICO, and passes it to PyInstaller for both executables.
2. **Windows installer:** Inno Setup uses the same ICO for the setup program and installed uninstall entry. Shortcut icons inherit the packaged engine executable icon.
3. **Android APK:** Buildozer uses the generated 512x512 PNG launcher icon. CI prepares and validates it before the APK build. Adaptive-icon safe zones and launcher cropping still require physical-device verification.
4. **Office interior:** add the emblem as the company wall plaque in the CEO room, with sufficient contrast and realistic scale; do not obscure navigation or department labels.
5. **Quality gates:** build Windows executables/installer and APK, inspect packaged assets, run desktop smoke tests, and test launcher cropping/startup on a physical Android device.

## Asset provenance and limitations

The hand-authored SVG and user-supplied raster are distinct assets. The virtual-office prototype uses the raster as a backdrop; the Android cockpit displays it above the VST wordmark when available. The packaging changes described here are staged in pull requests and are not yet proof of successful Windows build or visual verification. The previous Android build passed and produced an artifact before the new launcher-icon pipeline was added; the updated pipeline needs its own CI result. Physical-device checks remain outstanding.

## Acceptance checklist

- [x] Approved raster committed to `assets/branding/vst-approved-artwork.jpg`; original source retained at repository root.
- [x] Windows build script generates an ICO and supplies it to both PyInstaller executable builds.
- [x] Inno Setup configured to use the ICO for installer/uninstaller branding.
- [x] Android Buildozer configured to generate and package a PNG launcher icon from approved artwork.
- [x] Android cockpit uses the approved raster in its sidebar; virtual-office web scene uses it as background.
- [ ] Windows EXE/installer build passes and Explorer/taskbar appearance is inspected.
- [ ] Android launcher cropping/startup is verified on a physical device; adaptive icon support may need a separate pass.
- [ ] Add artwork as the company wall plaque in the CEO room.
- [ ] Confirm package contents in built distributables.
- [x] Branding-only changes leave execution mode, exchange permissions, and trading risk controls unchanged.
