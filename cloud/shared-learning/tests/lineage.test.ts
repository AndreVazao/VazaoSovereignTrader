import test from "node:test";
import assert from "node:assert/strict";
import { digestPublicPayload } from "../lib/provenance";
import { hasVerifiedLineage } from "../lib/lineage";

const now = Date.now();
const sourcePayload = { artifact_id: "source-001", strategy_id: "ema_atr_v1" };
const sourceArtifact = {
  id: "row-001",
  public_payload: sourcePayload,
  eligible: true,
  expires_at: new Date(now + 60_000).toISOString()
};
const sourceProvenance = {
  artifact_row_id: "row-001",
  payload_digest: digestPublicPayload(sourcePayload),
  verification_state: "verified",
  revoked_at: null
};

test("allows root artifacts without source references", () => {
  assert.equal(hasVerifiedLineage([], [], []), true);
});

test("accepts lineage only when every source is eligible and provenance is verified", () => {
  assert.equal(hasVerifiedLineage(["source-001"], [sourceArtifact], [sourceProvenance], now), true);
  assert.equal(hasVerifiedLineage(["source-001", "missing-source"], [sourceArtifact], [sourceProvenance], now), false);
  assert.equal(hasVerifiedLineage(["source-001"], [sourceArtifact, { ...sourceArtifact, id: "row-002" }], [sourceProvenance], now), false);
});

test("rejects expired, ineligible, revoked, unverified or tampered source artifacts", () => {
  assert.equal(hasVerifiedLineage(["source-001"], [{ ...sourceArtifact, eligible: false }], [sourceProvenance], now), false);
  assert.equal(hasVerifiedLineage(["source-001"], [{ ...sourceArtifact, expires_at: new Date(now - 1).toISOString() }], [sourceProvenance], now), false);
  assert.equal(hasVerifiedLineage(["source-001"], [sourceArtifact], [{ ...sourceProvenance, revoked_at: new Date(now).toISOString() }], now), false);
  assert.equal(hasVerifiedLineage(["source-001"], [sourceArtifact], [{ ...sourceProvenance, verification_state: "pending" }], now), false);
  assert.equal(hasVerifiedLineage(["source-001"], [{ ...sourceArtifact, public_payload: { ...sourcePayload, strategy_id: "tampered" } }], [sourceProvenance], now), false);
});
