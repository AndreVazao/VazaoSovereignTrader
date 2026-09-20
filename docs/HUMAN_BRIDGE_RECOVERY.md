# Human Bridge recovery policy

The Human Bridge keeps request metadata durable but keeps claim tokens and response values in RAM only.

Recovery rules:
- Pending requests expire into EXPIRED and cannot be answered.
- A pending request can receive a fresh claim token through the authenticated PC control plane after a restart.
- Reissuing a claim invalidates the previous token.
- Responded secrets are never persisted and are discarded on cancel or expiry.
- Browser session binding remains authoritative: a response cannot be applied to a replacement browser session.
- If the browser session itself is gone, the operator should create a new human request in the new session rather than replaying an old one.
