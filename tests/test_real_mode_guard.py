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


def test_configuration_can_disable_real_even_with_correct_phrase():
    guard = RealModeGuard({
        "enabled": True,
        "allow_real": False,
        "confirmation_phrase": "EU ACEITO O RISCO",
        "arm_seconds": 300,
    })
    ok, reason = guard.arm("EU ACEITO O RISCO")
    assert not ok
    assert "disabled by configuration" in reason
    assert not guard.snapshot()["armed"]


def test_guard_is_process_local_and_starts_disarmed():
    first = RealModeGuard({
        "enabled": True,
        "allow_real": True,
        "confirmation_phrase": "EU ACEITO O RISCO",
        "arm_seconds": 300,
    })
    ok, _ = first.arm("EU ACEITO O RISCO")
    assert ok
    assert first.snapshot()["armed"]

    restarted = RealModeGuard({
        "enabled": True,
        "allow_real": True,
        "confirmation_phrase": "EU ACEITO O RISCO",
        "arm_seconds": 300,
    })
    assert not restarted.snapshot()["armed"]
    ok, reason = restarted.can_enable_real()
    assert not ok
    assert "not armed" in reason


def test_engine_rejects_direct_real_transition_without_guard_authorization():
    from types import SimpleNamespace
    from PC_ENGINE.core.engine import SovereignEngine

    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {"autonomous_execution": {"allow_real": True}}
    engine.mode = "PAPER"
    engine.paper = True
    engine.state = SimpleNamespace(status="OFF", mode="PAPER")
    engine.paper_collector = None

    try:
        engine.set_mode("REAL")
    except RuntimeError as exc:
        assert "guarded operator authorization" in str(exc)
    else:
        raise AssertionError("direct REAL transition must be rejected")


def test_engine_rejects_real_when_configuration_disables_it():
    from types import SimpleNamespace
    from PC_ENGINE.core.engine import SovereignEngine

    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {"autonomous_execution": {"allow_real": False}}
    engine.mode = "PAPER"
    engine.paper = True
    engine.state = SimpleNamespace(status="OFF", mode="PAPER")
    engine.paper_collector = None

    try:
        engine.set_mode("REAL", real_authorized=True)
    except RuntimeError as exc:
        assert "disabled by configuration" in str(exc)
    else:
        raise AssertionError("REAL transition must be disabled by configuration")
