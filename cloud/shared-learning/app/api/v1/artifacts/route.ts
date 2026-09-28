import { createClient } from "@supabase/supabase-js";
import { createHash } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { publicPayload, validateArtifact } from "../../../../lib/artifact";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const MAX_BODY_BYTES = 32 * 1024;
const MAX_PAGE_SIZE = 100;
function clients() {
  const url=process.env.SUPABASE_URL, anon=process.env.SUPABASE_ANON_KEY, service=process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url||!anon||!service) throw new Error("service_not_configured");
  return {
    auth:createClient(url,anon,{auth:{persistSession:false,autoRefreshToken:false}}),
    db:createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}})
  };
}
async function principal(req:NextRequest) {
  const token=req.headers.get("authorization")?.match(/^Bearer\\s+(.+)$/i)?.[1];
  if (!token||token.length>8192) return null;
  const {auth}=clients();
  const {data,error}=await auth.auth.getUser(token);
  if (error||!data.user) return null;
  return data.user;
}
function fail(status:number,error:string) {
  return NextResponse.json({ok:false,error},{status,headers:{"Cache-Control":"no-store"}});
}
export async function POST(req:NextRequest) {
  try {
    const user=await principal(req);
    if (!user) return fail(401,"unauthorized");
    const declared=Number(req.headers.get("content-length")??0);
    if (declared>MAX_BODY_BYTES) return fail(413,"payload_too_large");
    const raw=await req.text();
    if (new TextEncoder().encode(raw).byteLength>MAX_BODY_BYTES) return fail(413,"payload_too_large");
    let body:unknown;
    try { body=JSON.parse(raw); } catch { return fail(400,"invalid_json"); }
    const artifact=validateArtifact(body);
    const payload=publicPayload(artifact);
    const digest=createHash("sha256").update(JSON.stringify(payload)).digest("hex");
    const {db}=clients();
    const {error}=await db.from("shared_learning_artifacts").upsert({
      owner_id:user.id,artifact_digest:digest,public_payload:payload,
      eligible:artifact.eligible,expires_at:new Date(artifact.expires_at_ms).toISOString()
    },{onConflict:"owner_id,artifact_digest",ignoreDuplicates:true});
    if (error) return fail(503,"storage_unavailable");
    return NextResponse.json({ok:true,accepted:true,digest},{status:201,headers:{"Cache-Control":"no-store"}});
  } catch (error) {
    const message=error instanceof Error?error.message:"";
    if (["unknown_or_private_fields","missing_fields","invalid_","artifact_","unsupported_"].some((prefix)=>message.startsWith(prefix))) return fail(400,message);
    return fail(503,"service_unavailable");
  }
}
export async function GET(req:NextRequest) {
  try {
    const user=await principal(req);
    if (!user) return fail(401,"unauthorized");
    const rawLimit=Number(req.nextUrl.searchParams.get("limit")??50);
    const limit=Number.isInteger(rawLimit)?Math.min(MAX_PAGE_SIZE,Math.max(1,rawLimit)):50;
    const {db}=clients();
    const {data,error}=await db.from("shared_learning_artifacts").select("public_payload")
      .eq("eligible",true).gt("expires_at",new Date().toISOString())
      .order("created_at",{ascending:false}).limit(limit);
    if (error) return fail(503,"storage_unavailable");
    return NextResponse.json({ok:true,artifacts:(data??[]).map((row)=>row.public_payload)},{headers:{"Cache-Control":"no-store"}});
  } catch { return fail(503,"service_unavailable"); }
}
