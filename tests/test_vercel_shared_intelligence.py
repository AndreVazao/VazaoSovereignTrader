from PC_ENGINE.core.vercel_shared_intelligence import VercelSharedIntelligenceProvider

def test_provider_uses_bootstrap_without_cursor(monkeypatch):
    p=VercelSharedIntelligenceProvider("https://intel.example","secret"); seen={}
    monkeypatch.setattr(p,"_request",lambda method,path,payload=None: seen.update(method=method,path=path) or {"rows":[]})
    p.pull(cursor=None,limit=10)
    assert seen["path"]=="/api/v1/intelligence/bootstrap?limit=10"

def test_provider_uses_incremental_cursor(monkeypatch):
    p=VercelSharedIntelligenceProvider("https://intel.example","secret"); seen={}
    monkeypatch.setattr(p,"_request",lambda method,path,payload=None: seen.update(method=method,path=path) or {"rows":[]})
    p.pull(cursor="abc",limit=10)
    assert seen["path"]=="/api/v1/intelligence/pull?limit=10&cursor=abc"
