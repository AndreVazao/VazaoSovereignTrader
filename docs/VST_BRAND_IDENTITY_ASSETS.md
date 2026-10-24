# VST brand identity and asset integration

## Canonical brand

- Product name: Vazão Sovereign Trader (VST).
- Existing vector emblem: `assets/branding/vst-logo.svg`.
- The cockpit prototype uses this emblem in the upper-left brand slot and as its SVG favicon.
- Keep the same emblem and blue/gold palette across the PC engine launcher, mobile APK, and digital-office executable. Runtime and trading logic must not depend on UI assets.

## Required distribution integration

1. **Windows Trader executable:** generate a Windows `.ico` from the approved source artwork and configure the PyInstaller/packaging icon option for `VazaoSovereignTrader.exe`.
2. **Digital office executable:** use the same `.ico` and show the emblem in the office shell header. Keep the office renderer optional and isolated from the headless engine.
3. **Android APK:** generate a density-adaptive launcher icon set from the approved artwork and wire it into the Android/Kivy packaging configuration. Verify adaptive foreground/background safe zones and launcher cropping on a physical device.
4. **Office interior:** add the emblem as the company wall plaque in the CEO room, with sufficient contrast and realistic scale; do not obscure navigation or department labels.
5. **Quality gates:** build both Windows executables and APK, inspect packaged assets, run desktop smoke tests, and test launcher cropping/startup on a physical Android device.

## Asset provenance and current limitation

The repository already contains a hand-authored vector emblem at `assets/branding/vst-logo.svg`. The cockpit change in this branch uses that existing SVG. The supplied raster artwork is present at repository root as `1792476724975.jpg` (408,588 bytes) and is now used as the virtual-office scene backdrop with a dark readability overlay. It should next be promoted to a descriptive canonical path under `assets/branding/` in a dedicated binary-safe move/commit. The SVG remains the current cockpit emblem/favicon; the raster has not yet been wired into the Windows executable icon, Android launcher icon, or packaged APK. Binary conversion and platform package rebuilds still require separate implementation and validation.

## Acceptance checklist

- [ ] Approved high-resolution raster artwork committed to `assets/branding/` with source filename and format verified.
- [ ] Windows icon generated from the approved artwork; both Trader and digital-office executables show it in Explorer/taskbar.
- [ ] APK launcher icon generated at required densities and verified on device.
- [ ] Office header and CEO wall plaque use the same approved artwork.
- [ ] Packaging/CI verifies assets exist and are included in each distributable.
- [ ] No change to execution mode, exchange permissions, or trading risk controls.
