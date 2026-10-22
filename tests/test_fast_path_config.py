import json
from pathlib import Path


def test_fast_path_is_disabled_and_real_blocked_by_default():
    path = Path("PC_ENGINE/config/config.example.json")
    config = json.loads(path.read_text(encoding="utf-8"))
    fast = config["fast_path"]
    assert fast["enabled"] is False
    assert fast["allow_real"] is False
    assert fast["max_signal_age_ms"] <= 1000


def test_autonomous_real_promotion_is_disabled_in_example_defaults():
    path = Path("PC_ENGINE/config/config.example.json")
    config = json.loads(path.read_text(encoding="utf-8"))
    autonomous = config["autonomous_execution"]
    assert autonomous["enabled"] is True
    assert autonomous["allow_real"] is False
    assert autonomous["auto_promote_real"] is False
