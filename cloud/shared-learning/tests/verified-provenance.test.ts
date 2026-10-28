import test from "node:test";
import assert from "node:assert/strict";
import { createHash, generateKeyPairSync, sign } from "node:crypto";
import type { SupabaseClient } from "@supabase/supabase-js";
import { digestPublicPayload, canonicalProvenanceMessage, parseProvenanceEnvelope } from "../lib/provenance";
import { verifyRegisteredProvenance } from "../lib/verified-provenance";

const ids = {
  organization_id: "123e4567-e89b-42d3-a456-426614174000",
  installation_id: "223e4567-e89b-42d3-a456-426614174000",
  agent_id: "323e4567-e89b-42d3-a456-426614174000",
  department_id: "423e4567-e89b-42d3-a456-426614174000"
};
const userId = "523e4567-e89b-42d3-a456-426614174000";
const payload = { schema_version: 1, strategy_id: "ema_atr_v1", sample_count: 100, producer_version: "0.1.0" };

function fixture(overrides: Record<string, unknown> = {}) {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const base = {
    schema_version: 1 as const,
    ...ids,
    artifact_id: "artifact-001",
    payload_digest: digestPublicPayload(payload),
    created_at_ms: Date.now(),
    producer_version: "0.1.0",
    source_artifact_ids: ["source-001"],
    signature: "pending"
  };
  const signature = sign(null, Buffer.from(canonicalProvenanceMessage({ ...base, signature: "" }), "utf8"), privateKey).toString("base64url");
  const envelope = parseProvenanceEnvelope({ ...base, signature, ...overrides });
  const publicKeyPem = publicKey.export({ type: "spki", format: "pem" }).toString();
  const keyFingerprint = createHash("sha256").update(publicKey.export({ type: "spki", format: "der" })).digest("hex");
  const records: Record<string, Record<string, unknown>> = {
    trader_organizations: { id: ids.organization_id, status: "active" },
    trader_organization_memberships: { organization_id: ids.organization_id, user_id: userId, role: "publisher", status: "active" },
    trader_installations: {
      id: ids.installation_id, organization_id: ids.organization_id,
      public_key_pem: publicKeyPem, key_fingerprint: keyFingerprint, status: "approved"
    },
    trader_agents: {
      id: ids.agent_id, organization_id: ids.organization_id, installation_id: ids.installation_id,
      department_id: ids.department_id, status: "active"
    },
    trader_departments: { id: ids.department_id, organization_id: ids.organization_id }
  };
  return { envelope, records };
}

function mockDb(records: Record<string, Record<string, unknown>>, mutate?: (table: string, row: Record<string, unknown>) => Record<string, unknown>) {
  const db = {
    from(table: string) {
      const filters: Array<[string, unknown]> = [];
      const builder = {
        select() { return builder; },
        eq(key: string, value: unknown) { filters.push([key, value]); return builder; },
        async maybeSingle() {
          let row = records[table];
          if (row && mutate) row = mutate(table, row);
          if (!row || filters.some(([key, value]) => row?.[key] !== value)) return { data: null, error: null };
          return { data: row, error: null };
        }
      };
      return builder;
    }
  };
  return db as unknown as SupabaseClient;
}

test("accepts provenance only when membership, installation, agent and department resolve", async () => {
  const { envelope, records } = fixture();
  const result = await verifyRegisteredProvenance(mockDb(records), userId, envelope, payload);
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.payloadDigest, digestPublicPayload(payload));
});

test("rejects non-publisher membership", async () => {
  const { envelope, records } = fixture();
  const db = mockDb(records, (table, row) => table === "trader_organization_memberships" ? { ...row, role: "reader" } : row);
  const result = await verifyRegisteredProvenance(db, userId, envelope, payload);
  assert.deepEqual(result, { ok: false, error: "organization_publish_forbidden", status: 403 });
});

test("rejects pending installation", async () => {
  const { envelope, records } = fixture();
  const db = mockDb(records, (table, row) => table === "trader_installations" ? { ...row, status: "pending" } : row);
  const result = await verifyRegisteredProvenance(db, userId, envelope, payload);
  assert.deepEqual(result, { ok: false, error: "installation_not_approved", status: 403 });
});

test("rejects payload tampering before registry authorization", async () => {
  const { envelope, records } = fixture();
  const result = await verifyRegisteredProvenance(mockDb(records), userId, envelope, { ...payload, sample_count: 101 });
  assert.deepEqual(result, { ok: false, error: "provenance_payload_digest_mismatch", status: 400 });
});

test("rejects cross-organization agent/department mismatch", async () => {
  const { envelope, records } = fixture();
  const db = mockDb(records, (table, row) => table === "trader_agents" ? { ...row, department_id: "623e4567-e89b-42d3-a456-426614174000" } : row);
  const result = await verifyRegisteredProvenance(db, userId, envelope, payload);
  assert.deepEqual(result, { ok: false, error: "agent_department_scope_invalid", status: 403 });
});


test("rejects an enrolled public key whose stored fingerprint does not match", async () => {
  const { envelope, records } = fixture();
  const db = mockDb(records, (table, row) => table === "trader_installations" ? { ...row, key_fingerprint: "0".repeat(64) } : row);
  const result = await verifyRegisteredProvenance(db, userId, envelope, payload);
  assert.deepEqual(result, { ok: false, error: "installation_key_fingerprint_mismatch", status: 503 });
});

test("rejects a suspended organization", async () => {
  const { envelope, records } = fixture();
  const db = mockDb(records, (table, row) => table === "trader_organizations" ? { ...row, status: "suspended" } : row);
  const result = await verifyRegisteredProvenance(db, userId, envelope, payload);
  assert.deepEqual(result, { ok: false, error: "organization_not_active", status: 403 });
});


test("rejects a provenance producer version that differs from the artifact", async () => {
  const { envelope, records } = fixture({ producer_version: "0.2.0" });
  const result = await verifyRegisteredProvenance(mockDb(records), userId, envelope, payload);
  assert.deepEqual(result, { ok: false, error: "provenance_producer_version_mismatch", status: 400 });
});
