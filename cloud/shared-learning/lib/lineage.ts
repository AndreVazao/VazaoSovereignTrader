import { digestPublicPayload } from "./provenance";

export type LineageArtifact = {
  id: string;
  public_payload: unknown;
  eligible: boolean;
  expires_at: string;
};

export type LineageProvenance = {
  artifact_row_id: string;
  payload_digest: string;
  verification_state: string;
  revoked_at: string | null;
};

/**
 * Treat source_artifact_ids as untrusted claims until every source resolves to
 * an eligible, unexpired artifact with active verified provenance and a
 * matching digest. Empty lineage is valid for root artifacts.
 */
export function hasVerifiedLineage(
  sourceArtifactIds: string[],
  artifacts: LineageArtifact[],
  provenanceRows: LineageProvenance[],
  nowMs = Date.now()
): boolean {
  if (sourceArtifactIds.length === 0) return true;
  const byPublicId = new Map<string, LineageArtifact>();
  for (const artifact of artifacts) {
    if (!artifact.public_payload || typeof artifact.public_payload !== "object" || Array.isArray(artifact.public_payload)) continue;
    const publicId = (artifact.public_payload as Record<string, unknown>).artifact_id;
    if (typeof publicId === "string") byPublicId.set(publicId, artifact);
  }
  const provenanceByRowId = new Map(provenanceRows.map((row) => [row.artifact_row_id, row] as const));
  return sourceArtifactIds.every((sourceId) => {
    const artifact = byPublicId.get(sourceId);
    if (!artifact || artifact.eligible !== true) return false;
    const expiresAt = Date.parse(artifact.expires_at);
    if (!Number.isFinite(expiresAt) || expiresAt <= nowMs) return false;
    const provenance = provenanceByRowId.get(artifact.id);
    if (!provenance || provenance.verification_state !== "verified" || provenance.revoked_at !== null) return false;
    try {
      return digestPublicPayload(artifact.public_payload) === provenance.payload_digest;
    } catch {
      return false;
    }
  });
}
