# VST brand identity and asset integration

## Canonical brand

- Product name: Vazão Sovereign Trader (VST).
- Existing vector emblem: `assets/branding/vst-logo.svg`.
- User-supplied raster artwork: `assets/branding/vst-approved-artwork.jpg` (canonical path; original source remains at repository root as `1792476724975.jpg`).
- Android package copy: `MOBILE_APP/vst-approved-artwork.jpg`, kept byte-identical to the canonical raster.
- The cockpit prototype uses the SVG emblem in the upper-left brand slot and as its favicon. The virtual-office prototype uses the approved raster as its scene backdrop with a dark readability overlay.
- Keep the same emblem and blue/gold palette across PC, Android and digital-office interfaces. Branding must remain independent of runtime trading logic.

## Required distribution integration

1. **Windows Trader executable:** generate a Windows `.ico` from the approved source artwork and configure the PyInstaller/packaging icon option for `VazaoSovereignTrader.exe`.
2. **Digital office executable:** use the same `.ico` and show the emblem in the office shell header. Keep the office renderer optional and isolated from the headless engine.
3. **Android APK:** generate a density-adaptive launcher icon set from the approved artwork and wire it into the Android/Kivy packaging configuration. Verify adaptive foreground/background safe zones and launcher cropping on a physical device.
4. **Office interior:** add the emblem as the company wall plaque in the CEO room, with sufficient contrast and realistic scale; do not obscure navigation or department labels.
5. **Quality gates:** build both Windows executables and APK, inspect packaged assets, run desktop smoke tests, and test launcher cropping/startup on a physical Android device.

## Asset provenance and current status

The repository contains both the hand-authored vector emblem and the user's raster artwork as distinct assets. The virtual-office web prototype uses the raster as its background; the Android cockpit packages the raster and displays it in its sidebar when available. The approved artwork is also staged for Windows icon generation and Android launcher artwork in dependent pull requests. Those changes do not by themselves prove that the final APK or Windows installer has been visually tested on physical devices.

## Acceptance checklist

- [x] Approved raster artwork committed to `assets/branding/vst-approved-artwork.jpg`; source retained at repository root.
- [x] Android cockpit packages the approved artwork; virtual-office web scene uses it as the background.
- [ ] Windows icon generated from the approved artwork; both Trader and digital-office executables show it in Explorer/taskbar.
- [ ] APK launcher icon generated at required densities and verified on device.
- [ ] Office header and CEO wall plaque use the same approved artwork.
- [ ] Packaging/CI verifies assets exist and are included in each distributable.
- [ ] No change to execution mode, exchange permissions, credentials, or trading risk controls; PAPER/read-only remains unchanged.
