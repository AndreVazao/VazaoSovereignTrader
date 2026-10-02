# Browser execution surface — concrete PAPER adapter

The first concrete transport for the generic execution-surface contract is
Playwright.

PlaywrightPaperSurfaceAdapter provides:
- Chromium startup in headed or headless mode;
- optional persistent local profile support;
- deterministic probe and observation feedback;
- PAPER BUY/SELL/CANCEL intent recording.

The adapter deliberately does not:
- click order controls;
- submit forms;
- call private exchange APIs;
- report a simulated PAPER action as an exchange fill.

Authentication remains outside the adapter. A persistent profile can be supplied
when a trader has already authenticated locally. Credentials, cookies, OTPs and
session secrets must never be committed to the repository.

CAPTCHA, anti-bot controls and MFA are not bypassed. If human interaction is
required, the Human Interaction Bridge remains the explicit path.

Operational browser health is separate from economic evidence, OOS uncertainty,
Risk Engine/readiness and REAL authorization. The adapter cannot authorize REAL.

The existing BrowserExecutionAdapter remains a separate, gated execution path
for future venue-specific integrations. This concrete Playwright adapter is
intentionally PAPER-only until a venue-specific implementation is independently
validated and connected to the existing authorization gates.


## Read-only platform reconnaissance

`inspect_current_page()` produces a bounded inventory of the current page's visible headings, button labels, navigation labels, form count, and visible input-type counts. It does not click or navigate through controls and does not read input values, cookies, browser storage, balances, positions, or credentials. The reported URL is limited to the origin; common email and long-number patterns in labels are redacted.

This is a first reconnaissance primitive, not a complete platform audit. Account balances, assets, permissions, market availability, fee schedules, and whether a feature can actually be used remain `UNKNOWN` until a separate, authorized, evidence-backed integration verifies them. The method is explicit and is not automatically invoked at startup.
