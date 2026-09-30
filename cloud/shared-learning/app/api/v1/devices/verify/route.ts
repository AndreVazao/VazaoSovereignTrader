import { createHash, timingSafeEqual } from "node:crypto";
import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";
import { parseDeviceId, verifyDeviceProof } from "../../../../../lib/identity";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BODY_BYTES = 8192;

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
async function principal(req: NextRequest) {
  const token = req.headers.get("authorization")?.match(/^Bearer\s+(.+)$/i)?.[1];
  if (!token || token.length > 8192) return null;
  const { auth } = clients();
  const { data, error } = await auth.auth.getUser(token);
  if (error || !data.user) return null;
  return data.user;
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
    if (!body || typeof body !== "object" || Array.isArray(body)) return fail(400, "invalid_proof_payload");
    const value = body as Record<string, unknown>;
    if (Object.keys(value).some((key) => !["device_id", "challenge_id", "challenge", "signature"].includes(key))) return fail(400, "unknown_proof_fields");
    let deviceId: string;
    let challengeId: string;
    try {
      deviceId = parseDeviceId(typeof value.device_id === "string" ? value.device_id : null);
      challengeId = parseDeviceId(typeof value.challenge_id === "string" ? value.challenge_id : null);
    } catch { return fail(400, "invalid_proof_identifier"); }
    if (typeof value.challenge !== "string" || value.challenge.length < 32 || value.challenge.length > 256 ||
        typeof value.signature !== "string" || value.signature.length < 80 || value.signature.length > 2048) {
      return fail(400, "invalid_proof_payload");
    }

    const { db } = clients();
    const { data: profile, error: profileError } = await db.from("user_profiles")
      .select("account_state,must_change_password").eq("user_id", user.id).maybeSingle();
    if (profileError) return fail(503, "profile_unavailable");
    if (!profile || profile.account_state !== "active" || profile.must_change_password !== false) return fail(403, "account_not_ready");

    const { data: withinLimit, error: rateLimitError } = await db.rpc("consume_device_security_rate_limit", {
      p_user_id: user.id, p_scope: "device.verify", p_limit: 8, p_window_seconds: 300
    });
    if (rateLimitError) return fail(503, "rate_limit_unavailable");
    if (withinLimit !== true) return fail(429, "rate_limit_exceeded");

    const { data: device, error: deviceError } = await db.from("authorized_devices")
      .select("id,status,device_public_key").eq("id", deviceId).eq("user_id", user.id).maybeSingle();
    if (deviceError) return fail(503, "device_unavailable");
    if (!device || device.status !== "pending") return fail(404, "pending_device_not_found");

    const now = new Date().toISOString();
    const { data: challengeRow, error: challengeError } = await db.from("device_proof_challenges")
      .select("id,challenge_sha256,expires_at,consumed_at")
      .eq("id", challengeId).eq("device_id", deviceId).eq("user_id", user.id)
      .is("consumed_at", null).gt("expires_at", now).maybeSingle();
    if (challengeError) return fail(503, "challenge_unavailable");
    if (!challengeRow) return fail(400, "challenge_invalid_or_expired");

    const suppliedDigest = createHash("sha256").update(value.challenge, "utf8").digest();
    const storedDigest = Buffer.from(challengeRow.challenge_sha256, "hex");
    if (suppliedDigest.length !== storedDigest.length || !timingSafeEqual(suppliedDigest, storedDigest)) {
      return fail(400, "challenge_mismatch");
    }

    // Verify before consuming so an invalid signature cannot burn a legitimate challenge.
    // The conditional update below is atomic; only one concurrent valid request can consume it.
    if (!verifyDeviceProof(device.device_public_key, value.challenge, value.signature)) {
      return fail(401, "device_proof_invalid");
    }
    const { data: consumed, error: consumeError } = await db.from("device_proof_challenges")
      .update({ consumed_at: now }).eq("id", challengeId).eq("user_id", user.id)
      .is("consumed_at", null).gt("expires_at", now).select("id").maybeSingle();
    if (consumeError) return fail(503, "challenge_consume_unavailable");
    if (!consumed) return fail(400, "challenge_already_used");

    const verifiedAt = new Date().toISOString();
    const { data: updated, error: updateError } = await db.from("authorized_devices")
      .update({ possession_verified_at: verifiedAt }).eq("id", deviceId).eq("user_id", user.id)
      .eq("status", "pending").select("id,device_fingerprint,possession_verified_at").maybeSingle();
    if (updateError) return fail(503, "device_proof_update_unavailable");
    if (!updated) return fail(409, "device_state_changed");
    return NextResponse.json({ ok: true, device: updated, message: "admin_approval_still_required" },
      { headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}
