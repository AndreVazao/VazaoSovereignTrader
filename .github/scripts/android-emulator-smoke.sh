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
adb logcat -d > "$EVIDENCE/logcat.txt"
# user_data_dir in the packaged app maps to the app-private files directory.
# Capture the full traceback, while never reading connection/token files.
if adb shell run-as "$PACKAGE" sh -c 'find /data/user/0/pt.andrevazao.vazaosovereigntrader/files -name startup_error.log -type f -print -exec cat {} \\;' > "$EVIDENCE/startup_error.txt" 2>/dev/null && [[ -s "$EVIDENCE/startup_error.txt" ]]; then
  echo "Startup diagnostic captured:"
  cat "$EVIDENCE/startup_error.txt"
else
  echo "No app-local startup traceback was available in the app-private files directory." > "$EVIDENCE/startup_error.txt"
fi
if grep -E "FATAL EXCEPTION|Process: ${PACKAGE}.*has died" "$EVIDENCE/logcat.txt"; then
  echo "Android application crash detected in logcat." | tee "$EVIDENCE/failure.txt"
  exit 1
fi

tesseract "$EVIDENCE/vst-home.png" stdout 2>/dev/null > "$EVIDENCE/screen-ocr.txt"
cat "$EVIDENCE/screen-ocr.txt"
if grep -qi "Tipo de erro:" "$EVIDENCE/screen-ocr.txt"; then
  echo "The app displayed its startup error fallback; inspect startup_error.txt." | tee "$EVIDENCE/failure.txt"
  exit 1
fi
grep -qi "Como posso ajudar" "$EVIDENCE/screen-ocr.txt"
