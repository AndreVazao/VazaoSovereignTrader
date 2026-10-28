# Cross-language canonicalization contract

Status: TypeScript and Python use RFC 8785/JCS for public payloads and provenance-message bytes. Shared payload vectors and a fixed Ed25519 provenance vector are now tested in both runtimes. The cross-runtime signature tests are a release gate and must pass on the exact current PR head before Python signing is enabled.

## Contract

- Canonical format: RFC 8785 / JSON Canonicalization Scheme (JCS).
- Hash: SHA-256 over the UTF-8 bytes of the canonical JSON string; digest output is lowercase hexadecimal.
- Object keys are sorted by UTF-16 code units, not locale, insertion order, or Python's Unicode code-point ordering.
- Numbers use ECMAScript JSON number serialization. In particular, negative zero serializes as `0`, and exponent formatting follows ECMAScript rules.
- Strings are JSON-escaped; unpaired UTF-16 surrogates are rejected.
- Only JSON values are accepted. Non-finite numbers, sparse arrays, non-plain objects, and undefined/function/symbol/BigInt values fail closed.
- Provenance signature bytes use the same canonical JSON function after the signature field has been excluded and identity/digest fields normalized by the envelope builder.

## Shared conformance vectors

The machine-readable fixture is `cloud/shared-learning/tests/fixtures/canonical-json-vectors.json`. TypeScript tests assert both exact canonical bytes and SHA-256 digests. The Python helper loads this exact fixture and asserts both values; it must not maintain a separate copy.

## Required before Python signing is enabled

1. Confirm Python and TypeScript CI pass the shared payload vectors on the exact same PR head.
2. Keep the shared Ed25519 golden vector passing in both runtimes; it verifies the exact message bytes and a fixed signature with a public key shared through the fixture.
3. Extend Python/TypeScript edge-case coverage for UTF-16 key ordering, Unicode escapes, fractional and exponent-form numbers, negative zero, and invalid surrogate sequences.
4. Confirm the exact-head CI passes the cross-runtime Ed25519 vector in both runtimes.
5. Keep Python signing disabled if any vector fails or the canonicalization library is unavailable.

This document is a compatibility gate, not evidence that the Python adapter already conforms. The existing Python adapter remains legacy/unattributed until the full signing and verified-read integration is reviewed. All work remains PAPER/read-only.
