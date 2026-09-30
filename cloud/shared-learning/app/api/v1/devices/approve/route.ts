import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";
import { parseDeviceId } from "../../../../../lib/identity";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BODY_BYTES = 4096;

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
    if (!body || typeof body !== "object" || Array.isArray(body)) return fail(400, "invalid_approval_payload");
    const value = body as Record<string, unknown>;
    if (Object.keys(value).some((key) => key !== "device_id")) return fail(400, "unknown_approval_fields");
    let deviceId: string;
    try { deviceId = parseDeviceId(typeof value.device_id === "string" ? value.device_id : null); }
    catch { return fail(400, "invalid_device_id"); }

    const { db } = clients();
    const { data: profile, error: profileError } = await db.from("user_profiles")
      .select("role,account_state,must_change_password").eq("user_id", user.id).maybeSingle();
    if (profileError) return fail(503, "profile_unavailable");
    if (!profile || profile.role !== "admin" || profile.account_state !== "active" || profile.must_change_password !== false) {
      return fail(403, "admin_required");
    }
    const { data, error } = await db.rpc("approve_authorized_device", {
      p_actor_user_id: user.id, p_device_id: deviceId
    });
    if (error) return fail(503, "device_approval_unavailable");
    if (data !== true) return fail(409, "device_not_eligible_for_approval");
    return NextResponse.json({ ok: true, approved: true }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}
