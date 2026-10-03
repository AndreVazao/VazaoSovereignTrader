# Vazao Sovereign Trader — Security Handoff (2026-10-03)

## Repository checkpoint

- Repository: `AndreVazao/VazaoSovereignTrader`
- Previous baseline before PR #328: `a0e9fcddbe7e61af0ffddf60eeb8fd828b17537d`.
- PR #328: https://github.com/AndreVazao/VazaoSovereignTrader/pull/328
- Branch: `fix/source-ingestion-redirect-egress-boundary`
- Final PR head tested by CI: `e477b638d52993cfdb1d38d38c92157451caee33`
- Merge commit: `ff8fb492a9f9ee31ad0c4cf2827f77554832cb12`
- Verified PR state: closed and merged.

## Changes delivered in PR #328

- Redirect source and target are both checked against the explicit source URL policy before following.
- Redirects remain same-origin and bounded by `max_redirects`; scheme-relative, non-HTTPS, out-of-policy, and cross-origin targets fail closed.
- The pinned HTTPS transport independently requires HTTPS on the default/443 port and refuses hosts not present in the validated DNS map.
- Regression tests cover invalid redirect sources, unsafe redirect targets, and a transport request to an unvalidated host.
- Source-ingestion documentation distinguishes application-level direct-connection pinning from host/network firewall enforcement.

## Exact-head verification

The following workflows completed successfully on PR head `e477b638d52993cfdb1d38d38c92157451caee33` before merge:

- Python tests — run `37112005346`: SUCCESS; test job and test-suite step completed successfully.
- Windows EXE — run `37112005356`: SUCCESS; EXE build, EXE smoke test, installer build, and installer smoke test completed successfully.

PR #328 was then squash-merged as `ff8fb492a9f9ee31ad0c4cf2827f77554832cb12`. Future code changes require a fresh exact-head CI check.

## Explicit limitations and safety

- DNS answers are validated as globally routable and the selected address is pinned for this fetch path; TLS retains hostname/SNI and certificate verification.
- Application code does not impose a host-wide firewall and cannot constrain unrelated processes. Host/network egress restrictions remain separate defense-in-depth work and must be configured/verified operationally.
- Cross-origin redirects are intentionally unsupported. If needed later, design per-target DNS validation and IP pinning before allowing that target to be contacted.
- Discovery only, read-only, opt-in, PAPER-only. No authenticated account access, order submission, transfers, reward claims, bot activation, cloud resources, secrets, or REAL-mode changes.
- Continue one branch/PR at a time. Never commit directly to `main`; merge only after reviewing the current diff and exact-head CI.
