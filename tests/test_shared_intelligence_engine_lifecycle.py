from types import SimpleNamespace

from PC_ENGINE.core.engine import SovereignEngine


def test_shared_intelligence_sync_waits_for_provider_configuration():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {
        "shared_intelligence": {
            "enabled": True,
            "sync_enabled": True,
            "sync_provider": "vercel",
        }
    }
    engine.state = SimpleNamespace(shared_intelligence={})
    engine.shared_intelligence_store = None
    engine.shared_intelligence_sync = None
    engine.shared_intelligence_worker = None

    engine._build_shared_intelligence_sync()

    assert engine.shared_intelligence_worker is None
    assert engine.state.shared_intelligence["state"] == "WAITING_FOR_PROVIDER_CONFIG"


def test_shared_intelligence_sync_disabled_by_default():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {
        "shared_intelligence": {
            "enabled": True,
            "sync_enabled": False,
        }
    }
    engine.state = SimpleNamespace(shared_intelligence={})
    engine.shared_intelligence_store = None
    engine.shared_intelligence_sync = None
    engine.shared_intelligence_worker = None

    engine._build_shared_intelligence_sync()

    assert engine.shared_intelligence_worker is None
    assert engine.state.shared_intelligence["state"] == "DISABLED"
