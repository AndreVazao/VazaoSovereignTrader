# Vazao Sovereign Trader — Security Handoff (2026-10-03)

## Repository checkpoint

- Repository: `AndreVazao/VazaoSovereignTrader`
- Baseline main SHA for this increment: `a0e9fcddbe7e61af0ffddf60eeb8fd828b17537d` (PR #327 merge).
- Current work: PR #328, https://github.com/AndreVazao/VazaoSovereignTrader/pull/328
- Branch: `fix/source-ingestion-redirect-egress-boundary`
- Scope: official-source ingestion redirect validation and transport-level egress boundary.

## Changes in PR #328

- Redirect source and target are both checked against the explicit source URL policy before following.
- Redirects remain same-origin and bounded by `max_redirects`; scheme-relative, non-HTTPS, out-of-policy, and cross-origin targets fail closed.
- The pinned HTTPS transport independently requires HTTPS on the default/443 port and refuses hosts not present in the validated DNS map.
- Regression tests cover invalid redirect sources, unsafe redirect targets, and a transport request to an unvalidated host.
- Source-ingestion documentation distinguishes application-level direct-connection pinning from host/network firewall enforcement.

## Verification status

- PR #328 head at handoff: `df02f10d3244a173bb883e926594162ce74ec266`.
- PR reports mergeable; no CI workflow runs or combined status checks were returned by the connector at the time this file was written. Do not merge until Python tests and Windows EXE/installer workflows pass on the exact latest PR head.
- Re-fetch PR #328 and its latest head SHA before checking workflows or merging. Any further commit requires exact-head CI to be checked again.
- Diff was inspected; changed files are `PC_ENGINE/opportunity/source_ingestion.py`, `tests/test_opportunity_source_ingestion.py`, and `docs/OPPORTUNITY_SOURCE_INGESTION.md`, plus this handoff note.

## Explicit limitations and safety

- DNS answers are validated as globally routable and the selected address is pinned for this fetch path; TLS retains hostname/SNI and certificate verification.
- Application code does not impose a host-wide firewall and cannot constrain unrelated processes. Host/network egress restrictions remain separate defense-in-depth work and must be configured/verified operationally.
- Cross-origin redirects are intentionally unsupported. If needed later, design per-target DNS validation and IP pinning before allowing that target to be contacted.
- Discovery only, read-only, opt-in, PAPER-only. No authenticated account access, order submission, transfers, reward claims, bot activation, cloud resources, secrets, or REAL-mode changes.
- Continue one branch/PR at a time. Never commit directly to `main`; merge only after reviewing the current diff and exact-head CI.
