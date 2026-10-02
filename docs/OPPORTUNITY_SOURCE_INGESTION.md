# Official Opportunity Source Ingestion — Safety Contract

## Scope

`PC_ENGINE/opportunity/source_ingestion.py` provides a bounded, read-only HTTP fetch primitive for explicitly configured public official sources. It does not crawl arbitrary URLs, access authenticated accounts, parse reward claims, infer personal eligibility, mutate the opportunity registry, or execute platform actions.

## Controls

- HTTPS only; exact lowercase host allowlist and approved path prefixes are required.
- URLs with embedded credentials or fragments are rejected.
- Redirect targets are checked against the same allowlist and redirect count is bounded.
- Requests use GET, a fixed research User-Agent, an explicit timeout, and an allowlisted text/JSON/XML content type.
- Declared and streamed response bodies are bounded by `max_bytes`; reads are capped at `max_bytes + 1` to detect overflow.
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
