import { createClient } from "@supabase/supabase-js";
import { createHash } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { publicPayload, validateArtifact } from "../../../../lib/artifact";
import { parseProvenanceEnvelope } from "../../../../lib/provenance";
import { verifyRegisteredProvenance } from "../../../../lib/verified-provenance";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BODY_BYTES = 32 * 1024;
const MAX_PAGE_SIZE = 100;

function clients() {
  const url = process.env.SUPABASE_URL;
  const anon = process.env.SUPABASE_ANON_KEY;
  const service = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !anon || !service) throw new Error("service_not_configured");
  return {
    auth: createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } }),
    db: createClient(url, service, { auth: { persistSession: false, autoRefreshToken: false } })
  };
}

async function principal(req: NextRequest) {
  const token = req.headers.get("authorization")?.match(/^Bearer\s+(.+)$/i)?.[1];
  if (!token || token.length > 8192) return null;
  const { auth } = clients();
  const { data, error } = await auth.auth.getUser(token);
  if (error || !data.user) return null;
  return data.user;
}

function fail(status: number, error: string) {
  return NextResponse.json({ ok: false, error }, { status, headers: { "Cache-Control": "no-store" } });
}

export async function POST(req: NextRequest) {
  try {
    const user = await principal(req);
    if (!user) return fail(401, "unauthorized");
    const declared = Number(req.headers.get("content-length") ?? 0);
    if (declared > MAX_BODY_BYTES) return fail(413, "payload_too_large");
    const raw = await req.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) return fail(413, "payload_too_large");

    let body: unknown;
    try { body = JSON.parse(raw); } catch { return fail(400, "invalid_json"); }

    let artifactInput: unknown = body;
    let provenanceInput: unknown;
    if (body && typeof body === "object" && !Array.isArray(body) && "artifact" in body) {
      const wrapped = body as Record<string, unknown>;
      if (Object.keys(wrapped).some((key) => key !== "artifact" && key !== "provenance")) {
        return fail(400, "unknown_request_fields");
      }
      if (!("provenance" in wrapped)) return fail(400, "missing_provenance");
      artifactInput = wrapped.artifact;
      provenanceInput = wrapped.provenance;
    }

    const artifact = validateArtifact(artifactInput);
    const payload = publicPayload(artifact);
    const digest = createHash("sha256").update(JSON.stringify(payload)).digest("hex");
    const { db } = clients();

    let verified: Awaited<ReturnType<typeof verifyRegisteredProvenance>> | undefined;
    let envelope: ReturnType<typeof parseProvenanceEnvelope> | undefined;
    if (provenanceInput !== undefined) {
      try { envelope = parseProvenanceEnvelope(provenanceInput); }
      catch (error) {
        return fail(400, error instanceof Error ? error.message : "invalid_provenance");
      }
      if (envelope.artifact_id !== artifact.artifact_id || envelope.payload_digest.toLowerCase() !== digest) {
        return fail(400, "provenance_artifact_or_digest_mismatch");
      }
      verified = await verifyRegisteredProvenance(db, user.id, envelope, payload);
      if (!verified.ok) return fail(verified.status, verified.error);
    }

    const { error: saveError } = await db.from("shared_learning_artifacts").upsert({
      owner_id: user.id,
      artifact_digest: digest,
      public_payload: payload,
      eligible: envelope ? false : artifact.eligible,
      expires_at: new Date(artifact.expires_at_ms).toISOString()
    }, { onConflict: "owner_id,artifact_digest", ignoreDuplicates: true });
    if (saveError) return fail(503, "storage_unavailable");

    if (envelope && verified && verified.ok) {
      const { data: stored, error: lookupError } = await db.from("shared_learning_artifacts")
        .select("id")
        .eq("owner_id", user.id)
        .eq("artifact_digest", digest)
        .maybeSingle();
      if (lookupError || !stored) return fail(503, "storage_unavailable");

      const { data: existing, error: provenanceLookupError } = await db.from("shared_learning_provenance")
        .select("organization_id,installation_id,agent_id,department_id,payload_digest,signature,verification_state")
        .eq("artifact_row_id", stored.id)
        .maybeSingle();
      if (provenanceLookupError) return fail(503, "provenance_storage_unavailable");

      if (existing) {
        const sameIdentity = existing.organization_id === envelope.organization_id &&
          existing.installation_id === envelope.installation_id &&
          existing.agent_id === envelope.agent_id &&
          existing.department_id === envelope.department_id &&
          existing.payload_digest === verified.payloadDigest &&
          existing.signature === envelope.signature &&
          existing.verification_state === "verified";
        if (!sameIdentity) return fail(409, "artifact_provenance_conflict");
      } else {
        const { error: provenanceSaveError } = await db.from("shared_learning_provenance").insert({
          artifact_row_id: stored.id,
          organization_id: envelope.organization_id,
          installation_id: envelope.installation_id,
          agent_id: envelope.agent_id,
          department_id: envelope.department_id,
          provenance_schema_version: envelope.schema_version,
          payload_digest: verified.payloadDigest,
          signature: envelope.signature,
          source_artifact_ids: verified.sourceArtifactIds,
          producer_version: verified.producerVersion,
          contributed_at: verified.contributedAt,
          verification_state: "verified",
          verified_at: new Date().toISOString()
        });
        if (provenanceSaveError) return fail(503, "provenance_storage_unavailable");
      }
      const { error: activateError } = await db.from("shared_learning_artifacts")
        .update({ eligible: artifact.eligible, expires_at: new Date(artifact.expires_at_ms).toISOString() })
        .eq("id", stored.id);
      if (activateError) return fail(503, "provenance_storage_unavailable");
    }

    return NextResponse.json({
      ok: true,
      accepted: true,
      digest,
      provenance: envelope ? "verified" : "legacy_unattributed"
    }, { status: 201, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "";
    if (["unknown_or_private_fields", "missing_fields", "invalid_", "artifact_", "unsupported_"].some((prefix) => message.startsWith(prefix))) {
      return fail(400, message);
    }
    return fail(503, "service_unavailable");
  }
}

export async function GET(req: NextRequest) {
  try {
    const user = await principal(req);
    if (!user) return fail(401, "unauthorized");
    const rawLimit = Number(req.nextUrl.searchParams.get("limit") ?? 50);
    const limit = Number.isInteger(rawLimit) ? Math.min(MAX_PAGE_SIZE, Math.max(1, rawLimit)) : 50;
    const { db } = clients();
    const { data, error } = await db.from("shared_learning_artifacts").select("public_payload")
      .eq("eligible", true).gt("expires_at", new Date().toISOString())
      .order("created_at", { ascending: false }).limit(limit);
    if (error) return fail(503, "storage_unavailable");
    return NextResponse.json({ ok: true, artifacts: (data ?? []).map((row) => row.public_payload) },
      { headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}
