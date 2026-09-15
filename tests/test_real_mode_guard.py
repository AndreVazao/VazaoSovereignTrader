from PC_ENGINE.core.real_mode_guard import RealModeGuard


def test_guard_rejects_wrong_phrase():
    guard = RealModeGuard({"enabled": True, "confirmation_phrase": "EU ACEITO O RISCO", "arm_seconds": 300})
    ok, _ = guard.arm("wrong")
    assert not ok
    assert guard.snapshot()["armed"] is False


def test_guard_authorization_is_one_time():
    guard = RealModeGuard({"enabled": True, "confirmation_phrase": "EU ACEITO O RISCO", "arm_seconds": 300})
    ok, _ = guard.arm("EU ACEITO O RISCO")
    assert ok
    ok, _ = guard.consume()
    assert ok
    ok, _ = guard.consume()
    assert not ok


def test_disabled_guard_cannot_arm():
    guard = RealModeGuard({"enabled": False, "confirmation_phrase": "EU ACEITO O RISCO"})
    ok, _ = guard.arm("EU ACEITO O RISCO")
    assert not ok
