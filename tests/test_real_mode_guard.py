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


def test_real_session_continues_after_one_time_guard_consumption():
    from types import SimpleNamespace
    from PC_ENGINE.core.engine import SovereignEngine

    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {"autonomous_execution": {"allow_real": True}}
    engine.mode = "REAL"
    engine.paper = False
    engine.real_operational = True
    engine.real_fail_safe_reason = ""
    engine.state = SimpleNamespace(mode="REAL", status="RUNNING")
    engine.real_mode_guard = RealModeGuard({
        "enabled": True,
        "allow_real": True,
        "confirmation_phrase": "EU ACEITO O RISCO",
        "arm_seconds": 300,
    })

    ok, _ = engine.real_mode_guard.arm("EU ACEITO O RISCO")
    assert ok
    ok, _ = engine.real_mode_guard.consume()
    assert ok
    assert not engine.real_mode_guard.snapshot()["armed"]
    assert engine.mode == "REAL"
    assert engine.real_operational


def test_real_fail_safe_switches_to_paper_and_disarms_guard():
    from types import SimpleNamespace
    from PC_ENGINE.core.engine import SovereignEngine

    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {"autonomous_execution": {"allow_real": True}}
    engine.mode = "REAL"
    engine.paper = False
    engine.real_operational = True
    engine.real_fail_safe_reason = ""
    engine.state = SimpleNamespace(mode="REAL", status="RUNNING")
    engine.paper_collector = None
    engine.real_mode_guard = RealModeGuard({
        "enabled": True,
        "allow_real": True,
        "confirmation_phrase": "EU ACEITO O RISCO",
        "arm_seconds": 300,
    })
    engine.real_mode_guard.arm("EU ACEITO O RISCO")
    engine.exchanges = {}
    engine._build_exchanges = lambda: {}
    engine._build_paper_collector = lambda: None
    engine.log = lambda *args, **kwargs: None

    engine.fail_safe_real("watchdog_exchange_failure")

    assert engine.mode == "PAPER"
    assert engine.paper
    assert not engine.real_operational
    assert engine.state.mode == "PAPER"
    assert engine.state.status == "SAFE_MODE"
    assert engine.real_fail_safe_reason == "watchdog_exchange_failure"
    assert not engine.real_mode_guard.snapshot()["armed"]
