import { createHash, createPublicKey, verify as cryptoVerify } from "node:crypto";

export const PROVENANCE_SCHEMA_VERSION = 1 as const;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SHA256 = /^[a-f0-9]{64}$/i;
const MAX_LINEAGE = 32;
const MAX_AGE_MS = 90 * 24 * 60 * 60 * 1000;
const MAX_FUTURE_SKEW_MS = 5 * 60 * 1000;

export type ProvenanceEnvelope = {
  schema_version: 1;
  organization_id: string;
  installation_id: string;
  agent_id: string;
  department_id: string;
  artifact_id: string;
  payload_digest: string;
  created_at_ms: number;
  producer_version: string;
  source_artifact_ids: string[];
  signature: string;
};

const FIELDS = [
  "schema_version", "organization_id", "installation_id", "agent_id", "department_id",
  "artifact_id", "payload_digest", "created_at_ms", "producer_version",
  "source_artifact_ids", "signature"
] as const;

function boundedString(value: unknown, max: number): value is string {
  return typeof value === "string" && value.length > 0 && value.trim() === value && value.length <= max;
}

export function parseProvenanceEnvelope(input: unknown, now = Date.now()): ProvenanceEnvelope {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("provenance_must_be_object");
  const value = input as Record<string, unknown>;
  if (Object.keys(value).some((key) => !(FIELDS as readonly string[]).includes(key))) throw new Error("unknown_provenance_fields");
  for (const key of FIELDS) if (!(key in value)) throw new Error("missing_provenance_fields");
  if (value.schema_version !== PROVENANCE_SCHEMA_VERSION) throw new Error("unsupported_provenance_schema");
  for (const key of ["organization_id", "installation_id", "agent_id", "department_id"] as const) {
    if (typeof value[key] !== "string" || !UUID.test(value[key] as string)) throw new Error("invalid_provenance_identity");
  }
  if (!boundedString(value.artifact_id, 128)) throw new Error("invalid_provenance_artifact_id");
  if (typeof value.payload_digest !== "string" || !SHA256.test(value.payload_digest)) throw new Error("invalid_provenance_digest");
  if (!Number.isSafeInteger(value.created_at_ms) || (value.created_at_ms as number) < now - MAX_AGE_MS ||
      (value.created_at_ms as number) > now + MAX_FUTURE_SKEW_MS) throw new Error("invalid_provenance_time");
  if (!boundedString(value.producer_version, 64)) throw new Error("invalid_provenance_producer");
  if (!Array.isArray(value.source_artifact_ids) || value.source_artifact_ids.length > MAX_LINEAGE ||
      value.source_artifact_ids.some((id) => !boundedString(id, 128)) ||
      new Set(value.source_artifact_ids).size !== value.source_artifact_ids.length) throw new Error("invalid_provenance_lineage");
  if (!boundedString(value.signature, 2048) || !/^[A-Za-z0-9_-]+$/.test(value.signature)) throw new Error("invalid_provenance_signature");
  return value as unknown as ProvenanceEnvelope;
}

/** Stable bytes to sign. The signature itself is excluded; identities must first be resolved against the trusted registry. */
export function canonicalProvenanceMessage(envelope: ProvenanceEnvelope): string {
  const signed = {
    schema_version: envelope.schema_version,
    organization_id: envelope.organization_id.toLowerCase(),
    installation_id: envelope.installation_id.toLowerCase(),
    agent_id: envelope.agent_id.toLowerCase(),
    department_id: envelope.department_id.toLowerCase(),
    artifact_id: envelope.artifact_id,
    payload_digest: envelope.payload_digest.toLowerCase(),
    created_at_ms: envelope.created_at_ms,
    producer_version: envelope.producer_version,
    source_artifact_ids: [...envelope.source_artifact_ids]
  };
  return JSON.stringify(signed);
}

function canonicalJson(value: unknown): string {
  if (typeof value === "number" && !Number.isFinite(value)) {
    throw new Error("non_finite_canonical_json_number");
  }
  if (typeof value === "bigint" || typeof value === "function" || typeof value === "symbol" ||
      typeof value === "undefined") {
    throw new Error("unsupported_canonical_json_value");
  }
  if (value === null || typeof value !== "object") {
    const encoded = JSON.stringify(value);
    if (encoded === undefined) throw new Error("unsupported_canonical_json_value");
    return encoded;
  }
  if (Array.isArray(value)) {
    const items: string[] = [];
    for (let index = 0; index < value.length; index += 1) {
      if (!(index in value)) throw new Error("sparse_canonical_json_array");
      items.push(canonicalJson(value[index]));
    }
    return "[" + items.join(",") + "]";
  }
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) {
    throw new Error("non_plain_canonical_json_object");
  }
  const record = value as Record<string, unknown>;
  return "{" + Object.keys(record).sort().map((key) =>
    JSON.stringify(key) + ":" + canonicalJson(record[key])
  ).join(",") + "}";
}

export function digestPublicPayload(payload: unknown): string {
  return createHash("sha256").update(canonicalJson(payload), "utf8").digest("hex");
}

/** registeredPublicKey must come from the server-side approved installation registry, never from the envelope. */
export function verifyProvenanceSignature(envelope: ProvenanceEnvelope, registeredPublicKey: string): boolean {
  try {
    const key = createPublicKey(registeredPublicKey);
    const algorithm = key.asymmetricKeyType === "ed25519" || key.asymmetricKeyType === "ed448" ? null : "sha256";
    return cryptoVerify(algorithm, Buffer.from(canonicalProvenanceMessage(envelope), "utf8"),
      key, Buffer.from(envelope.signature, "base64url"));
  } catch {
    return false;
  }
}
