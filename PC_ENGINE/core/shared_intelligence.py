from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
SHARED_FIELDS=frozenset({"schema_version","artifact_type","strategy_id","market","regime","horizon_seconds","sample_count","win_count","win_rate","mean_net_bps","median_net_bps","eligible","created_at_ms","producer_version","artifact_id","source_digest","source_owner_ref","source_node_ref","trust_score","source_count","expires_at_ms"})
@dataclass(frozen=True)
class SharedIntelligenceArtifact:
    artifact_type:str; strategy_id:str; market:str; regime:str; horizon_seconds:int; sample_count:int; win_count:int; win_rate:float; mean_net_bps:float; median_net_bps:float; eligible:bool; created_at_ms:int; producer_version:str="1"; artifact_id:str=""; source_digest:str=""; source_owner_ref:str=""; source_node_ref:str=""; trust_score:float=0.0; source_count:int=1; expires_at_ms:int=0
    def to_public_dict(self)->dict[str,Any]:
        return {"schema_version":1,**{k:getattr(self,k) for k in SHARED_FIELDS if k!="schema_version"}}
class SharedIntelligenceStore:
    def __init__(self,path:str|Path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    @staticmethod
    def validate_public_artifact(p:dict[str,Any])->dict[str,Any]:
        if not isinstance(p,dict) or set(p)-SHARED_FIELDS: raise ValueError("invalid_shared_artifact_fields")
        req=SHARED_FIELDS-{"producer_version"}; missing=req-set(p)
        if missing: raise ValueError("missing_fields:"+",".join(sorted(missing)))
        n,w=int(p["sample_count"]),int(p["win_count"]); rate=float(p["win_rate"])
        if n<0 or w<0 or w>n or not 0<=rate<=1 or not str(p["strategy_id"]).strip(): raise ValueError("invalid_shared_artifact_metrics")
        if not 0<=float(p.get("trust_score",0))<=1 or int(p.get("source_count",1))<1: raise ValueError("invalid_source_trust")
        if len(str(p.get("source_node_ref","")))>128 or len(str(p.get("source_owner_ref","")))>128: raise ValueError("source_ref_too_long")
        return dict(p)
    def append(self,a:SharedIntelligenceArtifact)->str:
        p=self.validate_public_artifact(a.to_public_dict()); d=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if not any(r.get("sha256")==d for r in self.read()):
            with self.path.open("a",encoding="utf-8") as f: f.write(json.dumps({"artifact":p,"sha256":d},sort_keys=True)+"\n")
        return d
    def read(self)->list[dict[str,Any]]:
        if not self.path.exists(): return []
        out=[]
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            r=json.loads(line); p=self.validate_public_artifact(r["artifact"]); d=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            if r.get("sha256")!=d: raise ValueError("artifact_integrity_mismatch")
            out.append(r)
        return out
@dataclass(frozen=True)
class SharedIntelligenceImportResult: accepted:int; rejected:int; skipped:int
class SharedIntelligenceImporter:
    def __init__(self,store:SharedIntelligenceStore,*,max_age_ms:int=86400000): self.store=store; self.max_age_ms=max(1,int(max_age_ms))
    def import_rows(self,rows:list[dict[str,Any]],*,now_ms:int)->SharedIntelligenceImportResult:
        a=r=s=0
        for row in rows:
            try:
                p=self.store.validate_public_artifact(row.get("artifact",row)); created=int(p["created_at_ms"]); exp=int(p.get("expires_at_ms",0) or 0)
                if created<=0 or now_ms-created>self.max_age_ms or now_ms<created or (exp and now_ms>=exp): s+=1; continue
                supplied=str(row.get("sha256","")); canonical=json.dumps(p,sort_keys=True,separators=(",",":"))
                if supplied and supplied!=hashlib.sha256(canonical.encode()).hexdigest(): r+=1; continue
                self.store.append(SharedIntelligenceArtifact(**{k:p[k] for k in SharedIntelligenceArtifact.__dataclass_fields__ if k in p})); a+=1
            except (TypeError,ValueError,KeyError,OverflowError): r+=1
        return SharedIntelligenceImportResult(a,r,s)
