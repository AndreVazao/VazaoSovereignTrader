import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";
import { digestPublicPayload } from "../../../../../lib/provenance";
import { hasVerifiedLineage } from "../../../../../lib/lineage";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_PAGE_SIZE = 100;
const SOURCE_QUERY_CHUNK = 100;

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

function fail(status: number, error: string) {
  return NextResponse.json({ ok: false, error }, { status, headers: { "Cache-Control": "no-store" } });
}

function chunks<T>(items: T[], size: number): T[][] {
  const result: T[][] = [];
  for (let i = 0; i < items.length; i += size) result.push(items.slice(i, i + size));
  return result;
}

export async function GET(req: NextRequest) {
  try {
    const token = req.headers.get("authorization")?.match(/^Bearer\\s+(.+)$/i)?.[1];
    if (!token || token.length > 8192) return fail(401, "unauthorized");
    const { auth, db } = clients();
    const { data: authData, error: authError } = await auth.auth.getUser(token);
    if (authError || !authData.user) return fail(401, "unauthorized");

    const rawLimit = Number(req.nextUrl.searchParams.get("limit") ?? 50);
    const limit = Number.isInteger(rawLimit) ? Math.min(MAX_PAGE_SIZE, Math.max(1, rawLimit)) : 50;
    const { data: provenanceRows, error: provenanceError } = await db.from("shared_learning_provenance")
      .select("artifact_row_id,organization_id,installation_id,agent_id,department_id,payload_digest,source_artifact_ids,producer_version,contributed_at,verification_state,revoked_at")
      .eq("verification_state", "verified")
      .is("revoked_at", null)
      .order("contributed_at", { ascending: false })
      .limit(limit);
    if (provenanceError) return fail(503, "provenance_storage_unavailable");
    if (!provenanceRows?.length) return NextResponse.json({ ok: true, artifacts: [] }, { headers: { "Cache-Control": "no-store" } });

    const artifactIds = provenanceRows.map((row) => row.artifact_row_id);
    const organizationIds = [...new Set(provenanceRows.map((row) => row.organization_id))];
    const installationIds = [...new Set(provenanceRows.map((row) => row.installation_id))];
    const agentIds = [...new Set(provenanceRows.map((row) => row.agent_id))];
    const departmentIds = [...new Set(provenanceRows.map((row) => row.department_id))];

    const [artifacts, organizations, installations, agents, departments] = await Promise.all([
      db.from("shared_learning_artifacts").select("id,public_payload,eligible,expires_at")
        .in("id", artifactIds).eq("eligible", true).gt("expires_at", new Date().toISOString()),
      db.from("trader_organizations").select("id,display_name,status").in("id", organizationIds).eq("status", "active"),
      db.from("trader_installations").select("id,organization_id,installation_label,status")
        .in("id", installationIds).eq("status", "approved"),
      db.from("trader_agents").select("id,organization_id,installation_id,department_id,display_name,status")
        .in("id", agentIds).eq("status", "active"),
      db.from("trader_departments").select("id,organization_id,display_name").in("id", departmentIds)
    ]);
    if ([artifacts, organizations, installations, agents, departments].some((result) => result.error)) {
      return fail(503, "provenance_registry_unavailable");
    }

    const artifactMap = new Map((artifacts.data ?? []).map((row) => [row.id, row] as const));
    const organizationMap = new Map((organizations.data ?? []).map((row) => [row.id, row] as const));
    const installationMap = new Map((installations.data ?? []).map((row) => [row.id, row] as const));
    const agentMap = new Map((agents.data ?? []).map((row) => [row.id, row] as const));
    const departmentMap = new Map((departments.data ?? []).map((row) => [row.id, row] as const));

    const sourceArtifactIds = [...new Set(provenanceRows.flatMap((row) => row.source_artifact_ids ?? []))];
    const sourceArtifactResults = await Promise.all(chunks(sourceArtifactIds, SOURCE_QUERY_CHUNK).map((ids) =>
      db.from("shared_learning_artifacts").select("id,public_payload,eligible,expires_at")
        .in("public_payload->>artifact_id", ids)
    ));
    if (sourceArtifactResults.some((result) => result.error)) return fail(503, "lineage_storage_unavailable");
    const sourceArtifacts = sourceArtifactResults.flatMap((result) => result.data ?? []);
    const sourceRowIds = [...new Set(sourceArtifacts.map((row) => row.id))];
    const sourceProvenanceResults = await Promise.all(chunks(sourceRowIds, SOURCE_QUERY_CHUNK).map((ids) =>
      db.from("shared_learning_provenance").select("artifact_row_id,payload_digest,verification_state,revoked_at")
        .in("artifact_row_id", ids)
    ));
    if (sourceProvenanceResults.some((result) => result.error)) return fail(503, "lineage_storage_unavailable");
    const sourceProvenance = sourceProvenanceResults.flatMap((result) => result.data ?? []);

    const result = provenanceRows.flatMap((row) => {
      const artifact = artifactMap.get(row.artifact_row_id);
      const organization = organizationMap.get(row.organization_id);
      const installation = installationMap.get(row.installation_id);
      const agent = agentMap.get(row.agent_id);
      const department = departmentMap.get(row.department_id);
      if (!artifact || !organization || !installation || !agent || !department ||
          digestPublicPayload(artifact.public_payload) !== row.payload_digest ||
          installation.organization_id !== row.organization_id ||
          agent.organization_id !== row.organization_id ||
          agent.installation_id !== row.installation_id ||
          agent.department_id !== row.department_id ||
          department.organization_id !== row.organization_id ||
          !hasVerifiedLineage(row.source_artifact_ids ?? [], sourceArtifacts, sourceProvenance)) return [];
      return [{
        artifact: artifact.public_payload,
        provenance: {
          schema_version: 1,
          organization_id: row.organization_id,
          organization_name: organization.display_name,
          installation_id: row.installation_id,
          installation_label: installation.installation_label,
          agent_id: row.agent_id,
          agent_name: agent.display_name,
          department_id: row.department_id,
          department_name: department.display_name,
          payload_digest: row.payload_digest,
          source_artifact_ids: row.source_artifact_ids,
          producer_version: row.producer_version,
          contributed_at: row.contributed_at,
          verification_state: "verified"
        }
      }];
    });

    return NextResponse.json({ ok: true, artifacts: result }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}
