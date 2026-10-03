import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";
import { endpointNonceDigest, parseEndpointProof, verifyEndpointRequest } from "../../../../../lib/device-endpoint-proof";
import { parseDeviceId } from "../../../../../lib/identity";
import { parseTailscaleAddress } from "../../../../../lib/tailscale-address";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BODY_BYTES = 4096;
const LEASE_SECONDS = 5 * 60;
const NONCE_TTL_SECONDS = 10 * 60;
const PATH = "/api/v1/devices/endpoint";

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
async function ready(db: ReturnType<typeof clients>["db"], userId: string) {
  const { data, error } = await db.from("user_profiles").select("account_state,must_change_password")
    .eq("user_id", userId).maybeSingle();
  if (error) throw new Error("profile_unavailable");
  return !!data && data.account_state === "active" && data.must_change_password === false;
}
async function rateLimit(db: ReturnType<typeof clients>["db"], userId: string, scope: string, limit: number) {
  const { data, error } = await db.rpc("consume_device_security_rate_limit", {
    p_user_id: userId, p_scope: scope, p_limit: limit, p_window_seconds: 300
  });
  if (error) throw new Error("rate_limit_unavailable");
  return data === true;
}
async function readBody(req: NextRequest): Promise<unknown | null> {
  const declared = Number(req.headers.get("content-length") ?? 0);
  if (declared > MAX_BODY_BYTES) throw new Error("payload_too_large");
  const raw = await req.text();
  if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) throw new Error("payload_too_large");
  try { return JSON.parse(raw); } catch { throw new Error("invalid_json"); }
}
function objectBody(body: unknown, allowed: string[]) {
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error("invalid_endpoint_payload");
  const value = body as Record<string, unknown>;
  if (Object.keys(value).some((key) => !allowed.includes(key))) throw new Error("unknown_endpoint_fields");
  return value;
}
function inputError(error: unknown) {
  const message = error instanceof Error ? error.message : "invalid_endpoint_payload";
  const status = message === "payload_too_large" ? 413 : 400;
  return fail(status, message);
}
async function consumeNonce(db: ReturnType<typeof clients>["db"], userId: string, deviceId: string, nonce: string) {
  const now = new Date();
  const expires = new Date(now.getTime() + NONCE_TTL_SECONDS * 1000);
  const { error } = await db.from("device_endpoint_request_nonces").insert({
    nonce_sha256: endpointNonceDigest(nonce), user_id: userId, device_id: deviceId,
    created_at: now.toISOString(), expires_at: expires.toISOString()
  });
  if (!error) return true;
  if (error.code === "23505") return false;
  throw new Error("endpoint_nonce_store_unavailable");
}
function signedMessage(userId: string, deviceId: string, timestamp: number, nonce: string, action: string, detail: string) {
  return ["v1", "POST", PATH, action, userId, deviceId, detail, String(timestamp), nonce].join("\n");
}

/**
 * Signed endpoint actions:
 * publish: { action, device_id, tailscale_address, timestamp, nonce, signature }
 * lookup:  { action, device_id, peer_device_id, timestamp, nonce, signature }
 * Signature is over the exact UTF-8 canonical message documented in docs/PRIVATE_ENDPOINT_LEASE_API.md.
 */
export async function POST(req: NextRequest) {
  try {
    const user = await principal(req);
    if (!user) return fail(401, "unauthorized");
    let value: Record<string, unknown>;
    try {
      value = objectBody(await readBody(req), [
        "action", "device_id", "peer_device_id", "tailscale_address", "timestamp", "nonce", "signature"
      ]);
    } catch (error) { return inputError(error); }
    if (value.action !== "publish" && value.action !== "lookup") return fail(400, "invalid_endpoint_action");

    let deviceId: string;
    let peerId: string | null = null;
    let address: string | null = null;
    let proof: ReturnType<typeof parseEndpointProof>;
    try {
      deviceId = parseDeviceId(typeof value.device_id === "string" ? value.device_id : null);
      if (value.action === "publish") address = parseTailscaleAddress(value.tailscale_address);
      else peerId = parseDeviceId(typeof value.peer_device_id === "string" ? value.peer_device_id : null);
      proof = parseEndpointProof(value);
    } catch (error) { return inputError(error); }

    const { db } = clients();
    if (!(await ready(db, user.id))) return fail(403, "account_not_ready");
    const scope = value.action === "publish" ? "endpoint.publish" : "endpoint.lookup";
    if (!(await rateLimit(db, user.id, scope, value.action === "publish" ? 60 : 120))) return fail(429, "rate_limit_exceeded");

    const ids = peerId ? [deviceId, peerId] : [deviceId];
    const { data: devices, error: deviceError } = await db.from("authorized_devices")
      .select("id,status,device_public_key").eq("user_id", user.id).in("id", ids);
    if (deviceError) return fail(503, "device_unavailable");
    const own = devices?.find((d) => d.id === deviceId && d.status === "approved");
    if (!own) return fail(404, "approved_device_not_found");
    const peer = peerId ? devices?.find((d) => d.id === peerId && d.status === "approved") : null;
    if (peerId && !peer) return fail(404, "approved_peer_not_found");

    const detail = value.action === "publish" ? address! : peerId!;
    const message = signedMessage(user.id, deviceId, proof.timestamp, proof.nonce, value.action, detail);
    if (!verifyEndpointRequest(own.device_public_key, message, proof.signature)) return fail(401, "device_proof_invalid");

    const nonceAccepted = await consumeNonce(db, user.id, deviceId, proof.nonce);
    if (!nonceAccepted) return fail(409, "endpoint_nonce_replayed");

    if (value.action === "publish") {
      const now = new Date();
      const expiresAt = new Date(now.getTime() + LEASE_SECONDS * 1000);
      const { data, error } = await db.from("device_endpoint_leases").upsert({
        device_id: deviceId, user_id: user.id, tailscale_address: address,
        announced_at: now.toISOString(), expires_at: expiresAt.toISOString()
      }, { onConflict: "device_id" }).select("device_id,announced_at,expires_at").single();
      if (error || !data) return fail(503, "endpoint_publish_unavailable");
      return NextResponse.json({ ok: true, lease: data, lease_seconds: LEASE_SECONDS,
        note: "routing_metadata_only_not_authorization" }, { headers: { "Cache-Control": "no-store" } });
    }

    const now = new Date().toISOString();
    const { data, error } = await db.from("device_endpoint_leases")
      .select("device_id,tailscale_address,announced_at,expires_at")
      .eq("user_id", user.id).eq("device_id", peerId).gt("expires_at", now).maybeSingle();
    if (error) return fail(503, "endpoint_lookup_unavailable");
    return NextResponse.json({ ok: true, endpoint: data ?? null,
      note: "routing_metadata_only_not_authorization" }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    if (error instanceof Error && error.message === "rate_limit_unavailable") return fail(503, error.message);
    if (error instanceof Error && error.message === "endpoint_nonce_store_unavailable") return fail(503, error.message);
    return fail(503, "service_unavailable");
  }
}

export async function GET() {
  return fail(405, "method_not_allowed_use_signed_post");
}
