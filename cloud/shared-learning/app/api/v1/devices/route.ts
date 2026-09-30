import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";
import { parseDeviceId, parseDeviceRegistration } from "../../../../lib/identity";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BODY_BYTES = 12 * 1024;

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
async function activeProfile(db: ReturnType<typeof clients>["db"], userId: string) {
  const { data, error } = await db.from("user_profiles").select("account_state,must_change_password").eq("user_id", userId).maybeSingle();
  if (error) throw new Error("profile_unavailable");
  return !!data && data.account_state === "active" && data.must_change_password === false;
}

export async function GET(req: NextRequest) {
  try {
    const user = await principal(req);
    if (!user) return fail(401, "unauthorized");
    const { db } = clients();
    if (!(await activeProfile(db, user.id))) return fail(403, "account_not_ready");
    const { data, error } = await db.from("authorized_devices")
      .select("id,device_label,device_fingerprint,status,created_at,approved_at,last_seen_at,revoked_at")
      .eq("user_id", user.id).order("created_at", { ascending: false }).limit(100);
    if (error) return fail(503, "devices_unavailable");
    return NextResponse.json({ ok: true, devices: data ?? [] }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
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
    let registration;
    try { registration = parseDeviceRegistration(body); }
    catch (error) { return fail(400, error instanceof Error ? error.message : "invalid_device_payload"); }
    const { db } = clients();
    if (!(await activeProfile(db, user.id))) return fail(403, "account_not_ready");
    const { data: withinLimit, error: rateLimitError } = await db.rpc("consume_device_security_rate_limit", {
      p_user_id: user.id, p_scope: "device.register", p_limit: 10, p_window_seconds: 300
    });
    if (rateLimitError) return fail(503, "rate_limit_unavailable");
    if (withinLimit !== true) return fail(429, "rate_limit_exceeded");
    const { data, error } = await db.from("authorized_devices").insert({
      user_id: user.id,
      device_public_key: registration.publicKey,
      device_label: registration.label,
      device_fingerprint: registration.fingerprint,
      status: "pending"
    }).select("id,device_label,device_fingerprint,status,created_at").single();
    if (error) {
      if (error.code === "23505") return fail(409, "device_already_registered");
      return fail(503, "device_registration_unavailable");
    }
    return NextResponse.json({ ok: true, device: data, message: "approval_required" }, { status: 201, headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const user = await principal(req);
    if (!user) return fail(401, "unauthorized");
    const { db } = clients();
    if (!(await activeProfile(db, user.id))) return fail(403, "account_not_ready");
    let id: string;
    try { id = parseDeviceId(req.nextUrl.searchParams.get("id")); }
    catch (error) { return fail(400, error instanceof Error ? error.message : "invalid_device_id"); }
    const { data, error } = await db.from("authorized_devices").update({ status: "revoked", revoked_at: new Date().toISOString() })
      .eq("id", id).eq("user_id", user.id).neq("status", "revoked").select("id").maybeSingle();
    if (error) return fail(503, "device_revocation_unavailable");
    if (!data) return fail(404, "device_not_found");
    return NextResponse.json({ ok: true, revoked: true }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}
