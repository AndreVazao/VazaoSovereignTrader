export const PUBLIC_FIELDS = [
  "schema_version","artifact_type","strategy_id","market","regime","horizon_seconds","sample_count","win_count","win_rate","mean_net_bps","median_net_bps","eligible","created_at_ms","producer_version","artifact_id","source_digest","trust_score","source_count","expires_at_ms"
] as const;
export type PublicArtifact = {
  schema_version: 1; artifact_type: string; strategy_id: string; market: string; regime: string;
  horizon_seconds: number; sample_count: number; win_count: number; win_rate: number;
  mean_net_bps: number; median_net_bps: number; eligible: boolean; created_at_ms: number;
  producer_version: string; artifact_id: string; source_digest: string; trust_score: number;
  source_count: number; expires_at_ms: number;
};
const isInt = (v: unknown): v is number => Number.isSafeInteger(v);
const isFiniteNumber = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const boundedString = (v: unknown, max = 128): v is string => typeof v === "string" && v.trim().length > 0 && v.length <= max;
export function validateArtifact(input: unknown, now = Date.now()): PublicArtifact {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("artifact_must_be_object");
  const p = input as Record<string, unknown>;
  if (Object.keys(p).some((key) => !(PUBLIC_FIELDS as readonly string[]).includes(key))) throw new Error("unknown_or_private_fields");
  for (const key of PUBLIC_FIELDS) if (!(key in p)) throw new Error("missing_fields");
  if (p.schema_version !== 1) throw new Error("unsupported_schema_version");
  if (!boundedString(p.artifact_type,64) || !boundedString(p.strategy_id) || !boundedString(p.market,64) || !boundedString(p.regime,64) || !boundedString(p.producer_version,64)) throw new Error("invalid_string_field");
  for (const key of ["horizon_seconds","sample_count","win_count","created_at_ms","source_count","expires_at_ms"]) if (!isInt(p[key]) || (p[key] as number) < 0) throw new Error("invalid_integer_field");
  if ((p.horizon_seconds as number)<1 || (p.sample_count as number)<1 || (p.win_count as number)>(p.sample_count as number) || (p.source_count as number)<1) throw new Error("invalid_counts");
  if (typeof p.eligible !== "boolean") throw new Error("invalid_eligible");
  if (!isFiniteNumber(p.win_rate)||p.win_rate<0||p.win_rate>1) throw new Error("invalid_win_rate");
  if (!isFiniteNumber(p.mean_net_bps)||!isFiniteNumber(p.median_net_bps)) throw new Error("invalid_net_stats");
  if (!isFiniteNumber(p.trust_score)||p.trust_score<0||p.trust_score>1) throw new Error("invalid_trust_score");
  if (typeof p.artifact_id!=="string"||p.artifact_id.length>128) throw new Error("invalid_artifact_id");
  if (typeof p.source_digest!=="string"||(p.source_digest!==""&&!/^[a-f0-9]{64}$/i.test(p.source_digest))) throw new Error("invalid_source_digest");
  if ((p.expires_at_ms as number)<=now||(p.created_at_ms as number)>now+300000) throw new Error("invalid_artifact_time");
  if ((p.created_at_ms as number)<now-90*24*60*60*1000) throw new Error("artifact_too_old");
  return p as unknown as PublicArtifact;
}
export function publicPayload(input: PublicArtifact) { return Object.fromEntries(PUBLIC_FIELDS.map((field) => [field,input[field]])); }
