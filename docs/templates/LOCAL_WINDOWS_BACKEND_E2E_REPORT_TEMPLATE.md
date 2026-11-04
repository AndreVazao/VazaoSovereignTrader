# VST Local Windows Backend E2E Validation Report

> Keep this report sanitized. Do not include secrets, full personal paths, private account IDs, or unrelated personal data. Use evidence references and hashes.

## 1. Executive summary

- Overall status: `NOT RUN` / `PASS` / `FAIL` / `BLOCKED` / `MIXED`
- Validation timestamp and timezone:
- Machine label: `old-target-pc`
- Operator/account context: primary ChatGPT account with Desktop Commander (do not record email in shared evidence)
- Exact PR/commit:
- Installer filename/version:
- Installer SHA-256:
- Evidence directory:
- Highest severity finding:
- End-to-end readiness conclusion:

## 2. Status definitions

- **PASS** — reproducible evidence meets the acceptance criteria.
- **FAIL** — observed behavior contradicts expected behavior.
- **BLOCKED** — cannot safely or validly run due to prerequisite/permission/build issue.
- **NOT RUN** — intentionally not attempted.
- **INCONCLUSIVE** — evidence is insufficient or ambiguous.

## 3. Machine baseline

| Item | Result | Evidence |
|---|---|---|
| Windows edition/build | | |
| Architecture | | |
| Free disk space | | |
| Current elevation state | | |
| Existing VST processes/services | | |
| Existing listening ports | | |
| Existing vault detected | | |
| Legacy learning DB detected | | |
| Vault backup created and verified | | |

## 4. Build and installer provenance

| Check | Status | Evidence/details |
|---|---|---|
| PR #522 exact HEAD verified | | |
| Required CI on exact HEAD | | |
| Windows EXE workflow succeeded on exact HEAD | | |
| Artifact/run ID | | |
| Artifact origin and checksum | | |
| Installer identity/version | | |
| Installed EXE SHA-256 | | |
| Install path separate from vault | | |

## 5. Test matrix

| ID | Test | Expected result | Status | Actual result | Evidence |
|---|---|---|---|---|---|
| PRE-01 | Exact build identity | Artifact matches exact approved HEAD | NOT RUN | | |
| PRE-02 | Existing vault and DB inventory | Identified without modification | NOT RUN | | |
| PRE-03 | Vault backup | Consistent backup verified before risky changes | NOT RUN | | |
| INS-01 | Installer execution | Installs without disabling security controls | NOT RUN | | |
| CFG-01 | Mode guard | Configured and effective mode both PAPER | NOT RUN | | |
| RT-01 | Headless engine start | One expected process, no privilege escalation | NOT RUN | | |
| RT-02 | API health | Liveness distinguished from engine-running | NOT RUN | | |
| RT-03 | Doctor/startup report | Status and failure reasons correctly reported | NOT RUN | | |
| RT-04 | Recovery integrity | Primary/backup recovery checks pass | NOT RUN | | |
| RT-05 | Heartbeat/worker status | Fresh heartbeat and expected workers | NOT RUN | | |
| SEC-01 | Network binding | Loopback/default safe binding; no public exposure | NOT RUN | | |
| SEC-02 | REAL-execution block | REAL routes remain unavailable/blocked | NOT RUN | | |
| LC-01 | Clean stop | Supported shutdown completes and process exits | NOT RUN | | |
| LC-02 | Restart/recovery | Engine restarts and recovers state | NOT RUN | | |
| LC-03 | No duplicate work | No duplicate pending task/execution | NOT RUN | | |
| MEM-01 | Synthetic learning write | Supported harmless record persists | NOT RUN | | |
| MEM-02 | Restart persistence | Synthetic record survives restart | NOT RUN | | |
| VAULT-01 | Vault location | Data outside versioned install directory | NOT RUN | | |
| VAULT-02 | Legacy migration | Source retained; result and failures visible | NOT RUN | | |
| VAULT-03 | Uninstall/reinstall | Vault survives actual verified cycle, or BLOCKED | NOT RUN | | |
| LOG-01 | Evidence sanitization | Shared artifacts contain no secrets | NOT RUN | | |

## 6. Timeline

| Timestamp | Action/event | PID/process | Result/exit code | Evidence |
|---|---|---|---|---|
| | | | | |

## 7. Runtime diagnostics

- API liveness:
- Engine running:
- Runtime readiness:
- Startup health status:
- Configured mode:
- Effective mode:
- Recovery integrity:
- Heartbeat age:
- Worker/collector health:
- Auth status (no tokens):
- REAL execution guard:
- Listening interfaces/ports:
- Sanitized diagnostics excerpt:

## 8. Vault and learning memory

- Resolved vault path (personal segments redacted):
- Manifest/schema version:
- Directory layout:
- Active SQLite DB path:
- DB integrity result:
- Safe record counts:
- Legacy DB present:
- Migration result:
- Backup location and verification:
- Restart persistence result:
- Uninstall/reinstall persistence:
- Data-loss or ambiguity risks:

## 9. Findings

### Critical
- None / list with evidence.

### High
- None / list with evidence.

### Medium
- None / list with evidence.

### Low
- None / list with evidence.

For each finding: ID, severity, confirmed/hypothesis, reproduction, expected vs actual, sanitized error excerpt, evidence, likely component, recommended fix.

## 10. Evidence index

| File | Timestamp | SHA-256 | What it proves | Sanitized? |
|---|---|---|---|---|
| | | | | |

## 11. Blocked and not-run tests

| Test | Status | Reason | Prerequisite needed |
|---|---|---|---|
| | | | |

## 12. Prioritized remediation plan

| Priority | Finding | Proposed fix | Test that proves fix |
|---|---|---|---|
| P0 | | | |
| P1 | | | |
| P2 | | | |

## 13. Final conclusion

- Can the backend be considered end-to-end operational on this PC? Why/why not?
- What is proven by evidence?
- What remains unproven?
- Is a further local test required?
- Exact artifacts/report paths:
