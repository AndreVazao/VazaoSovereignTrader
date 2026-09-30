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
