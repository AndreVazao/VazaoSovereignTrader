import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import {
  canonicalProvenanceMessage, digestPublicPayload, parseProvenanceEnvelope, verifyProvenanceSignature
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
    schema_version: 1,
    ...ids,
    artifact_id: "artifact-001",
    payload_digest: payloadDigest,
    created_at_ms: now,
    producer_version: "0.1.0",
    source_artifact_ids: ["source-001"],
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
  const other = generateKeyPairSync("ed25519").publicKey.export({ type: "spki", format: "pem" }).toString();
  assert.equal(verifyProvenanceSignature(envelope, other), false);
});

test("payload digest is stable for the same public JSON payload", () => {
  const payload = { strategy_id: "ema_atr_v1", sample_count: 100 };
  assert.equal(digestPublicPayload(payload), digestPublicPayload(payload));
  assert.match(digestPublicPayload(payload), /^[a-f0-9]{64}$/);
});
