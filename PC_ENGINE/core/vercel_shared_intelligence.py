from __future__ import annotations
import json,urllib.error,urllib.parse,urllib.request
from typing import Any
class VercelSharedIntelligenceProvider:
    """Provider for the Vercel advisory shared-intelligence service."""
    def __init__(self,base_url:str,token:str,*,timeout_seconds:float=5.0): self.base_url=base_url.rstrip("/");self.token=token;self.timeout_seconds=max(1.0,float(timeout_seconds))
    def _request(self,method:str,path:str,payload:dict[str,Any]|None=None)->dict[str,Any]:
        body=json.dumps(payload,separators=(",",":"),sort_keys=True).encode() if payload is not None else None
        headers={"Authorization":"Bearer "+self.token,"Accept":"application/json","Content-Type":"application/json"}
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base_url+path,data=body,headers=headers,method=method),timeout=self.timeout_seconds) as r:return json.loads(r.read().decode() or "{}")
        except (urllib.error.URLError,TimeoutError) as exc: raise RuntimeError("vercel_shared_intelligence_unavailable") from exc
    def pull(self,*,cursor:str|None,limit:int)->dict[str,Any]:
        q={"limit":str(max(1,min(int(limit),500)))}; 
        if cursor:q["cursor"]=cursor
        return self._request("GET","/api/v1/intelligence/"+("bootstrap" if not cursor else "pull")+"?"+urllib.parse.urlencode(q))
    def push(self,*,rows:list[dict[str,Any]])->dict[str,Any]: return self._request("POST","/api/v1/intelligence/push",{"rows":rows[:500]})
