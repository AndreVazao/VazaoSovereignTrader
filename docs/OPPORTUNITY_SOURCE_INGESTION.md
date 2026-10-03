# Official Opportunity Source Ingestion — Safety Contract

## Scope

`PC_ENGINE/opportunity/source_ingestion.py` provides a bounded, read-only HTTP fetch primitive for explicitly configured public official sources. It does not crawl arbitrary URLs, access authenticated accounts, parse reward claims, infer personal eligibility, mutate the opportunity registry, or execute platform actions.

## Controls

- HTTPS only; explicit lowercase DNS host allowlists are required. IP literals, single-label hosts, and obvious local/reserved development names (`localhost`, `.local`, `.internal`, `.test`, `.invalid`) are rejected.
- URLs with embedded credentials, fragments, non-standard ports, encoded path characters, backslashes, or dot-segment traversal are rejected.
- Path-prefix matching respects segment boundaries: `/api` may match `/api` and `/api/v1`, but not `/apix`.
- Redirect targets must match the explicit host/path allowlist, remain on the original origin, and stay within the configured redirect count. The redirect source is rechecked against policy before following. Scheme-relative targets, non-HTTPS targets, and cross-origin redirects are rejected.
- The pinned HTTPS handler independently requires HTTPS on port 443 and refuses any hostname without a prevalidated address. A redirect cannot silently cause the transport to connect to a host absent from the validated-IP map.
- Requests use GET, a fixed research User-Agent, an explicit timeout, and an allowlisted text/JSON/XML content type.
- Declared and streamed response bodies are bounded by `max_bytes`; reads are capped at `max_bytes + 1` to detect overflow.
- Caller-supplied retrieval timestamps must be positive integers; booleans, strings, floats, zero, and negative values are rejected.
- Each returned snapshot includes source ID, requested/final URL, retrieval timestamp, status, content type, byte length, and SHA-256 digest for provenance/deduplication.
- The fetcher returns raw bytes only. Parsing is a separate future step and must fail closed on malformed or ambiguous content.

## Usage pattern

Create an `OfficialSourceDefinition` per approved public source, including exact hosts and path prefixes. Do not use wildcards, arbitrary user-supplied hosts, URL shorteners, authenticated endpoints, account pages, or redirect chains to unapproved hosts. Source definitions should be reviewed and tested before activation.

## Explicit limitations

- No default venue allowlist is enabled by this module; callers must provide one.
- No scheduled fetching, recursive crawling, content interpretation, account eligibility check, registry write, dashboard integration, or automatic reward/bot/copy-trading action is included.
- Content hashes support comparison but do not prove that the publisher is authoritative or that the content is economically valid.
- Public pages can be stale or region-dependent. Any opportunity remains UNKNOWN until current account-specific eligibility is verified through an authorized, human-supervised path.

This module is discovery/evidence only. PAPER remains the default; it does not authorize orders, transfers, bot activation, reward claims, or REAL mode.

## Network-boundary note

The allowlist is a configuration trust boundary, not a general-purpose URL proxy. Only configure reviewed public official hostnames. DNS resolution rejects failures, empty answers, invalid addresses, and any answer that is not classified as globally routable; mixed public/private answer sets fail closed. The validated address is pinned for the actual TCP connection, TLS keeps the approved hostname for SNI and certificate verification, and ambient HTTP(S) proxy configuration is disabled for this fetch path.

Application-level pinning only constrains this fetcher's direct connection. It cannot enforce host firewall policy, control unrelated processes, or replace operating-system/network egress restrictions. Deployments that need a strict egress boundary should apply host/network firewall rules separately and verify them operationally. Do not describe application allowlisting as a host-wide firewall.

## Redirect and egress increment

The redirect handler validates both the current and destination URLs, rejects cross-origin changes, and enforces the configured redirect limit. The transport handler independently rejects non-HTTPS/non-443 requests and hosts absent from the validated DNS map. This deliberately fails closed rather than resolving and trusting a new redirect host mid-request. If future requirements need cross-origin redirects, implement a separate design that validates DNS and pins the target before that target is contacted; do not simply relax the origin check.
