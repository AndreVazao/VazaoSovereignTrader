import test from "node:test";
import assert from "node:assert/strict";
import { validateArtifact, publicPayload } from "../lib/artifact";

const now = Date.now();
function valid() {
  return {
    schema_version: 1, artifact_type: "strategy_summary", strategy_id: "ema_atr_v1",
    market: "BTC/USDT", regime: "trend", horizon_seconds: 300, sample_count: 100,
    win_count: 58, win_rate: 0.58, mean_net_bps: 3.2, median_net_bps: 2.1,
    eligible: true, created_at_ms: now - 1000, producer_version: "1",
    artifact_id: "sample-1", source_digest: "a".repeat(64), trust_score: 0.8,
    source_count: 2, expires_at_ms: now + 3600000
  };
}
test("accepts a well-formed public artifact", () => {
  assert.equal(validateArtifact(valid(), now).strategy_id, "ema_atr_v1");
});
test("rejects private and unknown fields", () => {
  assert.throws(() => validateArtifact({...valid(), owner_id: "spoofed"}, now), /unknown_or_private_fields/);
  assert.throws(() => validateArtifact({...valid(), balance: 100}, now), /unknown_or_private_fields/);
});
test("rejects invalid counts and expiry", () => {
  assert.throws(() => validateArtifact({...valid(), win_count: 101}, now), /invalid_counts/);
  assert.throws(() => validateArtifact({...valid(), expires_at_ms: now - 1}, now), /invalid_artifact_time/);
});
test("public projection only returns allow-listed artifact fields", () => {
  const payload = publicPayload(validateArtifact(valid(), now));
  assert.equal("owner_id" in payload, false);
  assert.equal("source_node_ref" in payload, false);
});
