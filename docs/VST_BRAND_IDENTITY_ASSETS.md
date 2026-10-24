# VST brand identity and asset integration

## Canonical brand

- Product name: Vazão Sovereign Trader (VST).
- Existing vector emblem: `assets/branding/vst-logo.svg`.
- User-supplied raster artwork: `assets/branding/vst-approved-artwork.jpg` (canonical path; original source remains at repository root as `1792476724975.jpg`).
- Android package copy: `MOBILE_APP/vst-approved-artwork.jpg`.
- The cockpit prototype uses the SVG emblem in the header and as favicon. The virtual-office prototype uses the supplied raster as its scene backdrop and adds a framed brand plaque in the CEO-office scene.
- Keep branding independent of runtime trading logic.

## Packaging integration status

- **Android cockpit:** displays approved artwork in the sidebar when available.
- **Android launcher icon:** PR #491 adds generation of a 512x512 PNG from the approved artwork and Buildozer configuration; CI result for that updated pipeline is pending.
- **Windows executable and installer icons:** PR #492 adds ICO generation and wires it to both PyInstaller executables and Inno Setup. Windows build/visual verification is pending.
- **Virtual office:** PR #489 stages the raster backdrop; the follow-up CEO wall plaque is in its own pull request. Browser rendering still needs review.

## Remaining acceptance gates

- [ ] CI passes for Android launcher icon generation and APK build.
- [ ] Physical Android device confirms launcher cropping and app startup.
- [ ] Windows EXE and installer build passes; Explorer/taskbar/installer artwork is visually inspected.
- [ ] CEO office wall plaque is reviewed at desktop and mobile viewport sizes.
- [ ] Verify each built distributable includes the intended image/icon.
- [x] Branding changes do not alter trading logic, exchange permissions, credentials, or execution mode; PAPER/read-only remains unchanged.
