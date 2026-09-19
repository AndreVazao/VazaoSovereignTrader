# Browser Automation

The Trader now contains an isolated browser execution layer for web-only trading platforms.

## What it does

- Persistent Chromium profile per platform.
- Manual login can be completed once; the browser profile keeps the session locally.
- Dry-run mode prepares the order form without submitting it.
- Live browser orders require both platform enablement and an explicit confirmation phrase.
- Every browser order attempt is written to JSONL.
- Browser errors can capture a screenshot as evidence.
- Platform selectors stay outside the core strategy/risk code.

## Installation

After installing the PC requirements, install the browser runtime:

    python -m playwright install chromium

## Security model

Browser automation is disabled by default.

Do not commit browser profiles, cookies, session storage, credentials, 2FA secrets, or screenshots containing private information.

Do not automate CAPTCHA or bypass anti-bot/security controls. The operator completes authentication challenges manually.

## Next step for each platform

For each web-only platform, create a local platform configuration with its URL and selectors. The generic connector supports symbol_input, quantity_input, buy_button, sell_button and order_confirmation.

The strategy/risk engine remains independent from browser mechanics. This allows the same signal/risk decision to be executed through API or browser without duplicating the trading logic.
