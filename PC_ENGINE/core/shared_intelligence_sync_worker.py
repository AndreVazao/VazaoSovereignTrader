from __future__ import annotations
import threading,time
from typing import Any
from .shared_intelligence import SharedIntelligenceStore
from .shared_intelligence_sync import SharedIntelligenceProvider,SharedIntelligenceSync
class SharedIntelligenceSyncWorker:
    """Best-effort background sync. Never controls execution or REAL authorization."""
    def __init__(self,store:SharedIntelligenceStore,sync:SharedIntelligenceSync,provider:SharedIntelligenceProvider,*,pull_interval_seconds:float=30.0,push_interval_seconds:float=60.0):
        self.sync=sync; self.provider=provider; self.pull_interval=max(1.0,float(pull_interval_seconds)); self.push_interval=max(1.0,float(push_interval_seconds)); self.stop_event=threading.Event(); self.thread=None; self.bootstrap_done=False; self.last_result={}
    def start(self):
        if self.thread and self.thread.is_alive(): return
        self.stop_event.clear(); self.thread=threading.Thread(target=self._run,name="shared-intelligence-sync",daemon=True); self.thread.start()
    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive(): self.thread.join(timeout=2.0)
    def run_once(self,*,bootstrap=False)->dict[str,Any]:
        result={"pull":self.sync.bootstrap(self.provider) if bootstrap else self.sync.sync_once(self.provider),"push":self.sync.push_new(self.provider)}
        self.last_result=result; return result
    def _run(self):
        next_pull=0.0; next_push=0.0
        while not self.stop_event.is_set():
            now=time.monotonic()
            try:
                if now>=next_pull:
                    self.last_result["pull"]=self.sync.bootstrap(self.provider) if not self.bootstrap_done else self.sync.sync_once(self.provider)
                    self.bootstrap_done=True; next_pull=now+self.pull_interval
                if now>=next_push:
                    self.last_result["push"]=self.sync.push_new(self.provider); next_push=now+self.push_interval
            except Exception:
                pass
            self.stop_event.wait(1.0)
