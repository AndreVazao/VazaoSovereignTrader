from PC_ENGINE.core.real_mode_guard import RealModeGuard


def test_wrong_phrase_is_rejected():
    guard = RealModeGuard({"enabled": True, "confirmation_phrase": "EU ACEITO O RISCO", "arm_seconds": 300})
    ok, _ = guard.arm("wrong")
    assert not ok
    assert not guard.snapshot()["armed"]


def test_authorization_is_consumed_once():
    guard = RealModeGuard({"enabled": True, "confirmation_phrase": "EU ACEITO O RISCO", "arm_seconds": 300})
    ok, _ = guard.arm("EU ACEITO O RISCO")
    assert ok
    ok, _ = guard.consume()
    assert ok
    ok, _ = guard.consume()
    assert not ok
