# Local test records

Store one report per local test session, preferably named:

`YYYY-MM-DDTHH-MM-SSZ_<short-commit>_windows-local-validation.md`

Do not overwrite previous reports. Preserve original console output and logs in a sibling folder when possible. Do not commit credentials, API tokens, private keys, exchange account details, personal files, or unrelated PC information.

## Required evidence
- Full commit SHA and GitHub Actions run/artifact identifiers.
- Windows version and architecture, Python/runtime details if relevant.
- Installer filename, byte size, SHA-256, and source artifact.
- Each test marked PASS / FAIL / BLOCKED / NOT RUN.
- Relevant command, exit code, sanitized output, and log path.
- Installation/uninstallation outcome and whether reboot was needed.
- Any process, port, crash, permission, or unexpected network activity observed.
- Final recommendation: READY_FOR_MORE_TESTS, BLOCKED, or ROLLBACK.

## Safety rules
- PAPER/read-only only. Never configure real exchange credentials or place orders.
- Never disable Defender, firewall, SmartScreen, TLS checks, or other security controls.
- Do not expose the local API to the LAN or internet. Keep loopback-only defaults.
- Do not run arbitrary commands copied from logs or network output.
- Stop on unexpected financial activity, public port binding, credential requests, unexplained admin escalation, or a process that cannot be stopped cleanly.
