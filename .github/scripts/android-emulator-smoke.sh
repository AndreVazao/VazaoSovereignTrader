#!/usr/bin/env bash
set -euo pipefail

cd "$GITHUB_WORKSPACE"
EVIDENCE="$GITHUB_WORKSPACE/test-artifacts/android"
mkdir -p "$EVIDENCE"
APK="$(find "$GITHUB_WORKSPACE" -type f -path '*/bin/*.apk' -print -quit)"
if [[ -z "$APK" ]]; then
  echo "No APK found under the workspace after the successful build step." | tee "$EVIDENCE/failure.txt"
  find "$GITHUB_WORKSPACE/MOBILE_APP" -maxdepth 5 -type f -name '*.apk' -print > "$EVIDENCE/apk-search.txt" || true
  exit 1
fi

echo "Installing emulator smoke-test APK: $APK"
PACKAGE="pt.andrevazao.vazaosovereigntrader"
trap 'adb logcat -d > "$EVIDENCE/logcat.txt" 2>/dev/null || true; adb exec-out screencap -p > "$EVIDENCE/vst-home.png" 2>/dev/null || true' EXIT

adb install "$APK"
adb logcat -c
maestro test .maestro/android-startup-smoke.yaml
adb shell monkey -p "$PACKAGE" 1
sleep 8
adb shell pidof "$PACKAGE"
adb exec-out screencap -p > "$EVIDENCE/vst-home.png"

# Capture the first-run chooser before selecting the virtual office.
adb exec-out screencap -p > "$EVIDENCE/vst-chooser.png"

# Kivy widgets do not consistently expose text to Android accessibility services.
# Use a stable relative screen point on the visible first-run office button, then
# verify the resulting screen with OCR rather than a false-negative text selector.
maestro test .maestro/android-office-smoke.yaml
sleep 3
adb shell pidof "$PACKAGE" >/dev/null
adb exec-out screencap -p > "$EVIDENCE/vst-office-entry.png"
tesseract "$EVIDENCE/vst-office-entry.png" stdout 2>/dev/null > "$EVIDENCE/office-ocr.txt"
cat "$EVIDENCE/office-ocr.txt"
if ! grep -Eqi "MARKET RADAR|MEMÓRIA CENTRAL|COMPARAÇÃO|CEO[[:space:]]+RADAR[[:space:]]+AN[ÁA]LISE|VIDA DO ESCRIT[ÓO]RIO" "$EVIDENCE/office-ocr.txt"; then
  echo "Virtual office content was not detected after selecting the office experience." | tee "$EVIDENCE/failure.txt"
  exit 1
fi

# Explicitly set logical display dimensions. Rotation settings alone can be ignored
# by portrait-locked apps/emulators, so the PNG dimensions are checked below too.
adb shell settings put system accelerometer_rotation 0
adb shell wm size 1080x1920
adb shell wm density 240
sleep 3
adb exec-out screencap -p > "$EVIDENCE/vst-portrait.png"
adb shell pidof "$PACKAGE" >/dev/null

adb shell wm size 1920x1080
adb shell settings put system user_rotation 1
sleep 4
adb exec-out screencap -p > "$EVIDENCE/vst-landscape.png"
adb shell pidof "$PACKAGE" >/dev/null

# Tablet-like landscape viewport, still running the office page.
adb shell wm size 1280x800
sleep 4
adb exec-out screencap -p > "$EVIDENCE/vst-tablet-landscape.png"
adb shell pidof "$PACKAGE" >/dev/null

# Assert that captures have the requested aspect ratios, not merely a live process.
python - "$EVIDENCE" <<'PYSCREEN'
import struct, sys
from pathlib import Path
root = Path(sys.argv[1])
expected = {
    "vst-portrait.png": "portrait",
    "vst-landscape.png": "landscape",
    "vst-tablet-landscape.png": "landscape",
}
for name, orientation in expected.items():
    data = (root / name).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"FAIL: {name} is not a valid PNG")
    width, height = struct.unpack(">II", data[16:24])
    print(f"{name}: {width}x{height}")
    if orientation == "portrait" and width >= height:
        raise SystemExit(f"FAIL: {name} should be portrait")
    if orientation == "landscape" and width <= height:
        raise SystemExit(f"FAIL: {name} should be landscape")
PYSCREEN

# Restore emulator display settings and capture diagnostics.
adb shell wm size reset
adb shell wm density reset
adb shell settings put system accelerometer_rotation 1
adb logcat -d > "$EVIDENCE/logcat.txt"
echo "PASS: office UI survived and screenshots have verified portrait/landscape dimensions." | tee "$EVIDENCE/orientation-smoke.txt"
# user_data_dir in the packaged app maps to the app-private files directory.
# Capture the full traceback, while never reading connection/token files.
if adb shell run-as "$PACKAGE" sh -c 'find /data/user/0/pt.andrevazao.vazaosovereigntrader -name startup_error.log -type f -print -exec cat {} +' > "$EVIDENCE/startup_error.txt" 2>/dev/null && [[ -s "$EVIDENCE/startup_error.txt" ]]; then
  echo "Startup diagnostic captured:"
  cat "$EVIDENCE/startup_error.txt"
else
  echo "No app-local startup traceback was available in the app-private files directory." > "$EVIDENCE/startup_error.txt"
fi
if grep -E "FATAL EXCEPTION|Process: ${PACKAGE}.*has died" "$EVIDENCE/logcat.txt"; then
  echo "Android application crash detected in logcat." | tee "$EVIDENCE/failure.txt"
  exit 1
fi

tesseract "$EVIDENCE/vst-chooser.png" stdout 2>/dev/null > "$EVIDENCE/screen-ocr.txt"
cat "$EVIDENCE/screen-ocr.txt"
if grep -qi "Tipo de erro:" "$EVIDENCE/screen-ocr.txt"; then
  echo "The app displayed its startup error fallback; inspect startup_error.txt." | tee "$EVIDENCE/failure.txt"
  exit 1
fi
if grep -Eqi "Como queres usar o Trader|Chat simples|Escritorio virtual|Escrit[oó]rio virtual" "$EVIDENCE/screen-ocr.txt"; then
  echo "PASS: first-run experience chooser is visible."
else
  echo "The first-run experience chooser was not detected." | tee "$EVIDENCE/failure.txt"
  exit 1
fi
if grep -Eqi "FATAL EXCEPTION|Process: ${PACKAGE}.*has died" "$EVIDENCE/logcat.txt"; then
  echo "Android application crash detected in logcat." | tee "$EVIDENCE/failure.txt"
  exit 1
fi