from __future__ import annotations
import json,time
from dataclasses import dataclass
from pathlib import Path
from typing import Any,Protocol
from .shared_intelligence import SharedIntelligenceImporter,SharedIntelligenceStore
class SharedIntelligenceProvider(Protocol):
    def pull(self,*,cursor:str|None,limit:int)->dict[str,Any]: ...
    def push(self,*,rows:list[dict[str,Any]])->dict[str,Any]: ...
@dataclass(frozen=True)
class SharedSyncState:
    cursor:str=""; last_pull_ms:int=0; last_push_ms:int=0; last_bootstrap_ms:int=0
class SharedIntelligenceSync:
    def __init__(self,store:SharedIntelligenceStore,state_path:str|Path,*,pull_limit:int=500):
        self.store=store; self.state_path=Path(state_path); self.state_path.parent.mkdir(parents=True,exist_ok=True); self.pull_limit=max(1,int(pull_limit))
    def _read_state(self):
        if not self.state_path.exists(): return SharedSyncState()
        x=json.loads(self.state_path.read_text()); return SharedSyncState(str(x.get("cursor","")),int(x.get("last_pull_ms",0)),int(x.get("last_push_ms",0)),int(x.get("last_bootstrap_ms",0)))
    def _write_state(self,s):
        t=self.state_path.with_suffix(".tmp"); t.write_text(json.dumps(s.__dict__,sort_keys=True)); t.replace(self.state_path)
    def bootstrap(self,provider,*,now_ms=None): return self.sync_once(provider,now_ms=now_ms,bootstrap=True)
    def sync_once(self,provider,*,now_ms=None,bootstrap=False):
        now=int(now_ms if now_ms is not None else time.time()*1000); st=self._read_state()
        try:
            res=provider.pull(cursor=None if bootstrap else st.cursor or None,limit=self.pull_limit); rows=res.get("rows",[]) if isinstance(res,dict) else []
            imp=SharedIntelligenceImporter(self.store).import_rows(rows,now_ms=now); cur=str(res.get("next_cursor",st.cursor)) if isinstance(res,dict) else st.cursor
            self._write_state(SharedSyncState(cur,now,st.last_push_ms,now if bootstrap else st.last_bootstrap_ms)); return {"accepted":imp.accepted,"rejected":imp.rejected,"skipped":imp.skipped}
        except Exception: return {"accepted":0,"rejected":0,"skipped":0}
    def push_new(self,provider,*,now_ms=None):
        now=int(now_ms if now_ms is not None else time.time()*1000); st=self._read_state(); rows=self.store.read()
        try:
            res=provider.push(rows=rows); self._write_state(SharedSyncState(str(res.get("next_cursor",st.cursor)),st.last_pull_ms,now,st.last_bootstrap_ms)); return {"uploaded":int(res.get("accepted",len(rows)))}
        except Exception: return {"uploaded":0}
