import { createHash, createPublicKey } from "node:crypto";
import type { SupabaseClient } from "@supabase/supabase-js";
import {
  type ProvenanceEnvelope,
  digestPublicPayload,
  verifyProvenanceSignature
} from "./provenance";

function registeredKeyFingerprint(publicKeyPem: string): string | null {
  try {
    const der = createPublicKey(publicKeyPem).export({ type: "spki", format: "der" });
    return createHash("sha256").update(der).digest("hex");
  } catch {
    return null;
  }
}

export type ProvenanceCheck =
  | { ok: true; payloadDigest: string; contributedAt: string; sourceArtifactIds: string[]; producerVersion: string }
  | { ok: false; error: string; status: number };

/**
 * Resolve every identity from server-owned records. No display name or key from
 * the submitted envelope is treated as proof of authorization.
 */
export async function verifyRegisteredProvenance(
  db: SupabaseClient,
  userId: string,
  envelope: ProvenanceEnvelope,
  publicPayload: unknown,
  now = Date.now()
): Promise<ProvenanceCheck> {
  const payloadDigest = digestPublicPayload(publicPayload);
  if (envelope.payload_digest.toLowerCase() !== payloadDigest) {
    return { ok: false, error: "provenance_payload_digest_mismatch", status: 400 };
  }

  const { data: organization, error: orgError } = await db
    .from("trader_organizations")
    .select("id,status")
    .eq("id", envelope.organization_id)
    .maybeSingle();
  if (orgError) return { ok: false, error: "provenance_registry_unavailable", status: 503 };
  if (!organization || organization.status !== "active") {
    return { ok: false, error: "organization_not_active", status: 403 };
  }

  const { data: membership, error: membershipError } = await db
    .from("trader_organization_memberships")
    .select("role,status")
    .eq("organization_id", envelope.organization_id)
    .eq("user_id", userId)
    .maybeSingle();
  if (membershipError) return { ok: false, error: "provenance_registry_unavailable", status: 503 };
  if (!membership || membership.status !== "active" ||
      !["owner", "admin", "publisher"].includes(membership.role)) {
    return { ok: false, error: "organization_publish_forbidden", status: 403 };
  }

  const { data: installation, error: installationError } = await db
    .from("trader_installations")
    .select("id,organization_id,public_key_pem,key_fingerprint,status")
    .eq("id", envelope.installation_id)
    .eq("organization_id", envelope.organization_id)
    .maybeSingle();
  if (installationError) return { ok: false, error: "provenance_registry_unavailable", status: 503 };
  if (!installation || installation.status !== "approved") {
    return { ok: false, error: "installation_not_approved", status: 403 };
  }

  const { data: agent, error: agentError } = await db
    .from("trader_agents")
    .select("id,organization_id,installation_id,department_id,status")
    .eq("id", envelope.agent_id)
    .eq("organization_id", envelope.organization_id)
    .eq("installation_id", envelope.installation_id)
    .eq("department_id", envelope.department_id)
    .maybeSingle();
  if (agentError) return { ok: false, error: "provenance_registry_unavailable", status: 503 };
  if (!agent || agent.status !== "active") {
    return { ok: false, error: "agent_department_scope_invalid", status: 403 };
  }

  const { data: department, error: departmentError } = await db
    .from("trader_departments")
    .select("id,organization_id")
    .eq("id", envelope.department_id)
    .eq("organization_id", envelope.organization_id)
    .maybeSingle();
  if (departmentError) return { ok: false, error: "provenance_registry_unavailable", status: 503 };
  if (!department) return { ok: false, error: "agent_department_scope_invalid", status: 403 };

  const keyFingerprint = registeredKeyFingerprint(installation.public_key_pem);
  if (!keyFingerprint || keyFingerprint !== installation.key_fingerprint) {
    return { ok: false, error: "installation_key_fingerprint_mismatch", status: 503 };
  }
  if (!verifyProvenanceSignature(envelope, installation.public_key_pem)) {
    return { ok: false, error: "provenance_signature_invalid", status: 401 };
  }
  const contributedAt = new Date(envelope.created_at_ms);
  if (!Number.isFinite(contributedAt.getTime()) || contributedAt.getTime() > now + 5 * 60 * 1000) {
    return { ok: false, error: "invalid_provenance_time", status: 400 };
  }

  return {
    ok: true,
    payloadDigest,
    contributedAt: contributedAt.toISOString(),
    sourceArtifactIds: [...envelope.source_artifact_ids],
    producerVersion: envelope.producer_version
  };
}
