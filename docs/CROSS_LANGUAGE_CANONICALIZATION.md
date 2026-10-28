# Cross-language canonicalization contract

Status: TypeScript canonical payload serialization and shared golden vectors are implemented in PR #504. Python compatibility is **not yet implemented or verified**. Do not enable Python-side signing or accept Python-generated digests until the Python adapter passes the same vectors byte-for-byte.

## Contract

- Canonical format: RFC 8785 / JSON Canonicalization Scheme (JCS).
- Hash: SHA-256 over the UTF-8 bytes of the canonical JSON string; digest output is lowercase hexadecimal.
- Object keys are sorted by UTF-16 code units, not locale, insertion order, or Python's Unicode code-point ordering.
- Numbers use ECMAScript JSON number serialization. In particular, negative zero serializes as `0`, and exponent formatting follows ECMAScript rules.
- Strings are JSON-escaped; unpaired UTF-16 surrogates are rejected.
- Only JSON values are accepted. Non-finite numbers, sparse arrays, non-plain objects, and undefined/function/symbol/BigInt values fail closed.
- Provenance signature bytes use the same canonical JSON function after the signature field has been excluded and identity/digest fields normalized by the envelope builder.

## Shared conformance vectors

The machine-readable fixture is `cloud/shared-learning/tests/fixtures/canonical-json-vectors.json`. TypeScript tests assert both exact canonical bytes and SHA-256 digests. The Python adapter must load this exact fixture and assert both values, not maintain a separate copy.

## Required before Python signing is enabled

1. Implement or adopt a reviewed RFC 8785 implementation in Python.
2. Add Python tests against the shared fixture and add envelope-signing golden vectors for the exact provenance message.
3. Include edge cases for UTF-16 key ordering, Unicode escapes, fractional and exponent-form numbers, negative zero, and invalid surrogate sequences.
4. Confirm Ed25519 signatures verify across runtimes using the same canonical message bytes.
5. Keep Python signing disabled if any vector fails or the canonicalization library is unavailable.

This document is a compatibility gate, not evidence that the Python adapter already conforms. The existing Python adapter remains legacy/unattributed until the full signing and verified-read integration is reviewed. All work remains PAPER/read-only.
