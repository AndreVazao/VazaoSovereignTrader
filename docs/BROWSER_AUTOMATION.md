# Browser Automation

The browser layer is limited to local observation, manual authentication and PAPER dry-run preparation.

## What it does

- Maintains a local Chromium/Playwright profile per configured platform.
- Allows the operator to complete login and security challenges manually.
- PAPER dry-run can prepare an order form but does not click the submit button.
- Records browser action attempts in JSONL and can capture diagnostic screenshots on errors.
- Keeps platform-specific selectors outside the core strategy and risk code.

## LIVE execution is hard-disabled

The VST browser connector rejects every request with `live=True` before opening or interacting with the trading page. This remains true even if local configuration contains `live_enabled: true`, disables confirmation, or supplies the expected confirmation phrase. Configuration cannot override the PAPER-only policy.

No browser order may be submitted by this connector. A future change to this policy requires a separate, explicit product decision and security review; do not re-enable it as part of ordinary development.

## Security model

- Browser automation remains disabled by default.
- Do not commit browser profiles, cookies, session storage, credentials, 2FA secrets, or screenshots containing private information.
- Do not automate CAPTCHA or bypass anti-bot/security controls. The operator completes authentication challenges manually.
- Do not use browser sessions for private account access, order submission, transfers or withdrawals.
- Keep the browser layer disconnected from the live connector registry.

## Installation

After installing the PC requirements, install the browser runtime:

    python -m playwright install chromium
