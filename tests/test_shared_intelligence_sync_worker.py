from pathlib import Path
from PC_ENGINE.core.shared_intelligence import SharedIntelligenceStore
from PC_ENGINE.core.shared_intelligence_sync import SharedIntelligenceSync
class Provider:
    def __init__(self): self.pulls=[]; self.pushes=[]
    def pull(self,*,cursor,limit): self.pulls.append((cursor,limit)); return {"rows":[],"next_cursor":"c1"}
    def push(self,*,rows): self.pushes.append(rows); return {"accepted":len(rows),"next_cursor":"c2"}
def test_sync_worker_contract(tmp_path:Path):
    from PC_ENGINE.core.shared_intelligence_sync_worker import SharedIntelligenceSyncWorker
    p=Provider(); s=SharedIntelligenceSync(SharedIntelligenceStore(tmp_path/"a.jsonl"),tmp_path/"state.json")
    w=SharedIntelligenceSyncWorker(s,sync=s,provider=p,pull_interval_seconds=1,push_interval_seconds=1)
    out=w.run_once(bootstrap=True)
    assert out["pull"]["accepted"]==0
    assert p.pulls[0][0] is None
