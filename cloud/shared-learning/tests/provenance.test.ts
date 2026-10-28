import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  canonicalProvenanceMessage, canonicalizePublicPayload, digestPublicPayload, parseProvenanceEnvelope, verifyProvenanceSignature
} from "../lib/provenance";

const now = Date.now();
const ids = {
  organization_id: "123e4567-e89b-42d3-a456-426614174000",
  installation_id: "223e4567-e89b-42d3-a456-426614174000",
  agent_id: "323e4567-e89b-42d3-a456-426614174000",
  department_id: "423e4567-e89b-42d3-a456-426614174000"
};

function unsigned(payloadDigest = "a".repeat(64)) {
  return {
    schema_version: 1 as const,
    ...ids,
    artifact_id: "artifact-001",
    payload_digest: payloadDigest,
    created_at_ms: now,
    producer_version: "0.1.0",
    source_artifact_ids: ["source-001", "source-002"],
    signature: "pending"
  };
}

function signed() {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const base = unsigned();
  const message = canonicalProvenanceMessage({ ...base, signature: "" });
  const signature = sign(null, Buffer.from(message, "utf8"), privateKey).toString("base64url");
  return { envelope: { ...base, signature }, publicKey: publicKey.export({ type: "spki", format: "pem" }).toString() };
}

test("parses a complete provenance envelope with immutable UUID identities", () => {
  const { envelope } = signed();
  assert.equal(parseProvenanceEnvelope(envelope, now).organization_id, ids.organization_id);
});

test("rejects client-supplied private fields and malformed identity", () => {
  const { envelope } = signed();
  assert.throws(() => parseProvenanceEnvelope({ ...envelope, owner_token: "secret" }, now), /unknown_provenance_fields/);
  assert.throws(() => parseProvenanceEnvelope({ ...envelope, organization_id: "João Pedro" }, now), /invalid_provenance_identity/);
});

test("rejects stale, future, duplicate and oversized lineage", () => {
  const { envelope } = signed();
  assert.throws(() => parseProvenanceEnvelope({ ...envelope, created_at_ms: now - 91 * 24 * 60 * 60 * 1000 }, now), /invalid_provenance_time/);
  assert.throws(() => parseProvenanceEnvelope({ ...envelope, created_at_ms: now + 6 * 60 * 1000 }, now), /invalid_provenance_time/);
  assert.throws(() => parseProvenanceEnvelope({ ...envelope, source_artifact_ids: ["same", "same"] }, now), /invalid_provenance_lineage/);
  assert.throws(() => parseProvenanceEnvelope({ ...envelope, source_artifact_ids: Array.from({ length: 33 }, (_, i) => String(i)) }, now), /invalid_provenance_lineage/);
});

test("verifies signature only against the supplied registered public key", () => {
  const { envelope, publicKey } = signed();
  assert.equal(verifyProvenanceSignature(envelope, publicKey), true);
  const tampered = { ...envelope, department_id: "523e4567-e89b-42d3-a456-426614174000" };
  assert.equal(verifyProvenanceSignature(tampered, publicKey), false);
  const reordered = { ...envelope, source_artifact_ids: [...envelope.source_artifact_ids].reverse() };
  assert.equal(verifyProvenanceSignature(reordered, publicKey), false);
  const other = generateKeyPairSync("ed25519").publicKey.export({ type: "spki", format: "pem" }).toString();
  assert.equal(verifyProvenanceSignature(envelope, other), false);
});

test("payload digest is canonical across object property order", () => {
  const first = { strategy_id: "ema_atr_v1", sample_count: 100, nested: { z: 2, a: 1 } };
  const reordered = { nested: { a: 1, z: 2 }, sample_count: 100, strategy_id: "ema_atr_v1" };
  assert.equal(digestPublicPayload(first), digestPublicPayload(reordered));
  assert.match(digestPublicPayload(first), /^[a-f0-9]{64}$/);
});


test("rejects values that are not valid JSON before computing a public payload digest", () => {
  assert.throws(() => digestPublicPayload({ value: Number.NaN }), /non_finite_canonical_json_number/);
  assert.throws(() => digestPublicPayload({ value: Number.POSITIVE_INFINITY }), /non_finite_canonical_json_number/);
  assert.throws(() => digestPublicPayload({ value: undefined }), /unsupported_canonical_json_value/);
  assert.throws(() => digestPublicPayload([, 1]), /sparse_canonical_json_array/);
  assert.throws(() => digestPublicPayload({ value: new Date(0) }), /non_plain_canonical_json_object/);
  assert.throws(() => digestPublicPayload({ value: 1n }), /unsupported_canonical_json_value/);
  assert.throws(() => digestPublicPayload({ value: () => "not-json" }), /unsupported_canonical_json_value/);
  assert.throws(() => digestPublicPayload({ value: Symbol("not-json") }), /unsupported_canonical_json_value/);
  assert.throws(() => digestPublicPayload({ nested: [1, undefined] }), /unsupported_canonical_json_value/);
});

test("normalizes negative zero as JSON number zero for TypeScript payload digests", () => {
  assert.equal(digestPublicPayload({ metric: -0 }), digestPublicPayload({ metric: 0 }));
});


test("canonical JSON matches shared RFC 8785/JCS golden vectors", () => {
  const fixture = JSON.parse(readFileSync(join(__dirname, "fixtures", "canonical-json-vectors.json"), "utf8")) as {
    format: string;
    vectors: Array<{ name: string; input: unknown; canonical: string; sha256: string }>;
  };
  assert.equal(fixture.format, "RFC8785-JCS");
  for (const vector of fixture.vectors) {
    assert.equal(canonicalizePublicPayload(vector.input), vector.canonical, vector.name);
    assert.equal(digestPublicPayload(vector.input), vector.sha256, vector.name);
  }
});

test("rejects lone UTF-16 surrogates in strings and object keys", () => {
  assert.throws(() => canonicalizePublicPayload({ value: "\\ud800" }), /unpaired_canonical_json_surrogate/);
  assert.throws(() => canonicalizePublicPayload({ ["\\udfff"]: 1 }), /unpaired_canonical_json_surrogate/);
});
