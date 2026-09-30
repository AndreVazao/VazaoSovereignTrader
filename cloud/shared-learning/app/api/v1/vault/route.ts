import { createHash } from "node:crypto";
import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BODY_BYTES = 1_500_000;
const ALLOWED_KINDS = new Set(["profile_backup", "selected_config", "recovery_bundle"]);

function clients() {
  const url = process.env.SUPABASE_URL;
  const anon = process.env.SUPABASE_ANON_KEY;
  const service = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !anon || !service) throw new Error("service_not_configured");
  return {
    auth: createClient(url, anon, { auth: { persistSession: false, autoRefreshToken: false } }),
    db: createClient(url, service, { auth: { persistSession: false, autoRefreshToken: false } }),
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
function validBase64(value: unknown, maxLength: number): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= maxLength &&
    /^[A-Za-z0-9+/]+={0,2}$/.test(value) && value.length % 4 === 0;
}
function validId(value: string | null): value is string {
  return !!value && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

export async function GET(req: NextRequest) {
  try {
    const user = await principal(req);
    if (!user) return fail(401, "unauthorized");
    const { db } = clients();
    if (!(await activeProfile(db, user.id))) return fail(403, "account_not_ready");
    const id = req.nextUrl.searchParams.get("id");
    if (id) {
      if (!validId(id)) return fail(400, "invalid_vault_id");
      const { data, error } = await db.from("encrypted_vault_objects")
        .select("id,object_kind,ciphertext,encryption_version,nonce,salt,ciphertext_sha256,created_at,expires_at")
        .eq("id", id).eq("owner_id", user.id).is("deleted_at", null).or(`expires_at.is.null,expires_at.gt.${new Date().toISOString()}`).maybeSingle();
      if (error) return fail(503, "vault_unavailable");
      if (!data) return fail(404, "vault_object_not_found");
      const actualDigest = createHash("sha256").update(data.ciphertext).digest("hex");
      if (actualDigest !== data.ciphertext_sha256) return fail(503, "vault_integrity_check_failed");
      return NextResponse.json({ ok: true, object: data }, { headers: { "Cache-Control": "no-store" } });
    }
    const { data, error } = await db.from("encrypted_vault_objects")
      .select("id,object_kind,encryption_version,ciphertext_sha256,created_at,expires_at")
      .eq("owner_id", user.id).is("deleted_at", null).or(`expires_at.is.null,expires_at.gt.${new Date().toISOString()}`).order("created_at", { ascending: false }).limit(100);
    if (error) return fail(503, "vault_unavailable");
    return NextResponse.json({ ok: true, objects: data ?? [] }, { headers: { "Cache-Control": "no-store" } });
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
    if (!body || typeof body !== "object" || Array.isArray(body)) return fail(400, "invalid_vault_payload");
    const value = body as Record<string, unknown>;
    if (Object.keys(value).some((key) => !["object_kind", "ciphertext", "encryption_version", "nonce", "salt", "expires_at"].includes(key))) {
      return fail(400, "unknown_vault_fields");
    }
    if (typeof value.object_kind !== "string" || !ALLOWED_KINDS.has(value.object_kind)) return fail(400, "invalid_vault_object_kind");
    if (value.encryption_version !== 1) return fail(400, "unsupported_encryption_version");
    if (!validBase64(value.ciphertext, 1_400_000) || !validBase64(value.nonce, 32) || !validBase64(value.salt, 64)) return fail(400, "invalid_vault_envelope");
    if (Buffer.from(value.nonce, "base64").byteLength !== 12 || Buffer.from(value.salt, "base64").byteLength !== 16) return fail(400, "invalid_vault_envelope");
    let expiresAt: string | null = null;
    if (value.expires_at !== undefined && value.expires_at !== null) {
      if (typeof value.expires_at !== "string" || !Number.isFinite(Date.parse(value.expires_at)) || Date.parse(value.expires_at) <= Date.now()) return fail(400, "invalid_vault_expiry");
      expiresAt = new Date(value.expires_at).toISOString();
    }
    const { db } = clients();
    if (!(await activeProfile(db, user.id))) return fail(403, "account_not_ready");
    const digest = createHash("sha256").update(value.ciphertext).digest("hex");
    const { data, error } = await db.from("encrypted_vault_objects").insert({
      owner_id: user.id,
      object_kind: value.object_kind,
      ciphertext: value.ciphertext,
      encryption_version: value.encryption_version,
      nonce: value.nonce,
      salt: value.salt,
      ciphertext_sha256: digest,
      expires_at: expiresAt,
    }).select("id,object_kind,encryption_version,ciphertext_sha256,created_at,expires_at").single();
    if (error) return fail(503, "vault_save_unavailable");
    return NextResponse.json({ ok: true, object: data }, { status: 201, headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const user = await principal(req);
    if (!user) return fail(401, "unauthorized");
    const id = req.nextUrl.searchParams.get("id");
    if (!validId(id)) return fail(400, "invalid_vault_id");
    const { db } = clients();
    if (!(await activeProfile(db, user.id))) return fail(403, "account_not_ready");
    const { data, error } = await db.from("encrypted_vault_objects")
      .update({ deleted_at: new Date().toISOString() })
      .eq("id", id).eq("owner_id", user.id).is("deleted_at", null).select("id").maybeSingle();
    if (error) return fail(503, "vault_delete_unavailable");
    if (!data) return fail(404, "vault_object_not_found");
    return NextResponse.json({ ok: true, deleted: true }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return fail(503, "service_unavailable");
  }
}
