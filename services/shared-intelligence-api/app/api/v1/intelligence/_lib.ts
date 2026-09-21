import { get, list, put } from "@vercel/blob";
import { createHash, timingSafeEqual } from "node:crypto";
const MAX_BATCH=500, MAX_AGE_MS=86400000;
const SHARED_FIELDS=new Set(["schema_version","artifact_type","strategy_id","market","regime","horizon_seconds","sample_count","win_count","win_rate","mean_net_bps","median_net_bps","eligible","created_at_ms","producer_version","artifact_id","source_digest","source_owner_ref","source_node_ref","trust_score","source_count","expires_at_ms"]);
export type Envelope={artifact:Record<string,unknown>;sha256:string};
function canonical(value:unknown){return JSON.stringify(value,Object.keys(value as object).sort());}
function sha256(value:unknown){return createHash("sha256").update(canonical(value)).digest("hex");}
function auth(request:Request){const expected=process.env.SHARED_INTELLIGENCE_SYNC_TOKEN;if(!expected)return false;const supplied=request.headers.get("authorization")?.replace(/^Bearer\\s+/i,"")??"";const a=Buffer.from(supplied),b=Buffer.from(expected);return a.length===b.length&&timingSafeEqual(a,b);}
export function requireAuth(request:Request){if(!auth(request))throw new Response("Unauthorized",{status:401});}
export function validateArtifact(payload:Record<string,unknown>){for(const key of Object.keys(payload))if(!SHARED_FIELDS.has(key))throw new Error("private_or_unknown_field:"+key);const sample=Number(payload.sample_count),wins=Number(payload.win_count),rate=Number(payload.win_rate);if(!Number.isInteger(sample)||sample<0||!Number.isInteger(wins)||wins<0||wins>sample)throw new Error("invalid_counts");if(!Number.isFinite(rate)||rate<0||rate>1)throw new Error("invalid_win_rate");if(!String(payload.strategy_id??"").trim())throw new Error("strategy_id_required");const artifactId=String(payload.artifact_id??"");if(artifactId.length>128)throw new Error("artifact_id_too_long");const sourceDigest=String(payload.source_digest??"");if(sourceDigest&&(sourceDigest.length!==64||!/^[0-9a-f]+$/i.test(sourceDigest)))throw new Error("invalid_source_digest");const trust=Number(payload.trust_score??0);if(!Number.isFinite(trust)||trust<0||trust>1)throw new Error("invalid_trust_score");const sourceCount=Number(payload.source_count??1);if(!Number.isInteger(sourceCount)||sourceCount<1)throw new Error("invalid_source_count");if(!Number.isFinite(Number(payload.created_at_ms)))throw new Error("created_at_ms_required");const expiry=Number(payload.expires_at_ms??0);if(!Number.isFinite(expiry)||expiry<0)throw new Error("invalid_expiry");for(const key of ["source_owner_ref","source_node_ref"])if(String(payload[key]??"").length>128)throw new Error("source_ref_too_long");return payload;}
async function readBlob(pathname:string):Promise<Envelope|null>{
  try{
    const result=await get(pathname,{access:"private",useCache:false});
    if(!result||result.statusCode!==200||!result.stream)return null;
    const value=JSON.parse(await new Response(result.stream).text());
    return value?.artifact&&value?.sha256?value:null;
  }catch{return null;}
}

async function readPage(cursor:string|null,limit:number){
  const prefix=process.env.SHARED_INTELLIGENCE_BLOB_PREFIX||"shared-intelligence/";
  const page=await list({prefix,cursor:cursor||undefined,limit:Math.min(Math.max(limit,1),MAX_BATCH)});
  const rows:Envelope[]=[];
  for(const blob of page.blobs){
    const value=await readBlob(blob.pathname);
    if(value)rows.push(value);
  }
  return {rows,next_cursor:page.cursor??""};
}

export async function appendUnique(rows:Envelope[]){
  let accepted=0;
  const prefix=process.env.SHARED_INTELLIGENCE_BLOB_PREFIX||"shared-intelligence/";
  for(const row of rows.slice(0,MAX_BATCH)){
    try{
      const artifact=validateArtifact(row.artifact);
      const digest=sha256(artifact);
      if(digest!==row.sha256)continue;
      const created=Number(artifact.created_at_ms);
      if(!Number.isInteger(created)||created<=0)continue;
      const pathname=prefix+String(created).padStart(13,"0")+"-"+digest+".json";
      await put(pathname,JSON.stringify({artifact,sha256:digest}),{access:"private",contentType:"application/json",addRandomSuffix:false,allowOverwrite:false});
      accepted++;
    }catch{}
  }
  return accepted;
}

export async function pullRows(cursor:string|null,limit:number){
  return readPage(cursor,limit);
}

export function isFresh(artifact:Record<string,unknown>,now=Date.now()){const created=Number(artifact.created_at_ms),expires=Number(artifact.expires_at_ms??0);return created>0&&now>=created&&now-created<=MAX_AGE_MS&&(!expires||now<expires);}
