# Official opportunity source policy boundary

## Scope

`PC_ENGINE/opportunity/source_policy.py` is a local, metadata-only validation boundary for future official-source ingestion. It does not perform HTTP requests, follow redirects, crawl websites, log into accounts, or trigger claims, orders, transfers, bots or subscriptions.

## Explicit trust

Callers must construct `OfficialSourcePolicy` with an explicit set of exact hostnames. An empty allowlist rejects every source. Subdomains are not implicitly trusted, and deceptive suffixes such as `www.binance.com.attacker.example` do not match `www.binance.com`.

Accepted URLs must use HTTPS, standard port 443, a hostname in the exact allowlist, no embedded username/password, and no fragment. IP-literal hosts are rejected. Hostnames are lowercased and a trailing dot is removed for comparison.

## Observation metadata

A validated `SourceObservation` stores the canonical source URL, observation time, source-capture time, SHA-256 digest of the evidence supplied by the caller, and optionally the final URL. It stores no page body or credentials. Timestamps must be positive integer milliseconds and cannot be materially in the future; the capture time cannot materially follow observation time. The digest must be 64 lowercase hexadecimal characters.

If a caller supplies a final URL, it must pass the same allowlist policy and remain on the exact same origin as the source URL. Cross-origin redirects are rejected even if the destination is separately allowlisted; a future fetch adapter must explicitly revalidate the destination and create a new observation instead of silently trusting a redirect.

The `fingerprint` is a stable SHA-256 digest of canonical source URL, capture timestamp and evidence digest. It can be used by a later ledger to detect duplicate evidence; this module does not persist records or claim that duplicate suppression is already wired into the opportunity registry.

## Safety and next steps

- No network access occurs in this module; callers provide URLs and evidence metadata.
- Do not add credentials, account balances, private pages or raw sensitive account data to evidence artifacts.
- Future fetch adapters must be separately reviewed and add timeout/size limits, redirect policy, content-type checks, rate limits, source freshness, and deterministic tests before they are enabled.
- This policy cannot authorize execution and must remain separate from readiness, preflight, Risk Engine, RealModeGuard, operator approval and reconciliation.
