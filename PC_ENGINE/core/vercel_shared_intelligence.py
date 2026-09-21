from __future__ import annotations
import json, urllib.error, urllib.parse, urllib.request
from typing import Any
class VercelSharedIntelligenceProvider:
    """Provider adapter for the Vercel shared-intelligence API. Only privacy-safe artifacts are sent."""
    def __init__(self, base_url:str, token:str, *, timeout_seconds:float=5.0): self.base_url=base_url.rstrip("/"); self.token=token; self.timeout_seconds=max(1.0,float(timeout_seconds))
    def _request(self, method:str, path:str, payload:dict[str,Any]|None=None)->dict[str,Any]:
        body=None; headers={"Authorization":"Bearer "+self.token,"Accept":"application/json"}
        if payload is not None: body=json.dumps(payload,separators=(",",":"),sort_keys=True).encode("utf-8"); headers["Content-Type"]="application/json"
        request=urllib.request.Request(self.base_url+path,data=body,headers=headers,method=method)
        try:
            with urllib.request.urlopen(request,timeout=self.timeout_seconds) as response: raw=response.read().decode("utf-8")
        except (urllib.error.URLError,TimeoutError) as exc: raise RuntimeError("vercel_shared_intelligence_unavailable") from exc
        return json.loads(raw) if raw else {}
    def pull(self, *, cursor:str|None, limit:int)->dict[str,Any]:
        params={"limit":str(max(1,min(int(limit),500)))}
        if cursor: params["cursor"]=cursor
        return self._request("GET","/api/v1/intelligence/pull?"+urllib.parse.urlencode(params))
    def push(self, *, rows:list[dict[str,Any]])->dict[str,Any]: return self._request("POST","/api/v1/intelligence/push",{"rows":rows[:500]})
