from types import SimpleNamespace

from PC_ENGINE.core.engine import SovereignEngine


def _engine(*, status="RUNNING", learning_enabled=True, learning_memory=object(),
            watchdog=None, mode="PAPER", real_operational=False):
    events = []
    state = SimpleNamespace(
        status=status,
        watchdog=watchdog or {},
        health_isolation={},
    )
    return SimpleNamespace(
        state=state,
        config={"learning_memory": {"enabled": learning_enabled}},
        mode=mode,
        learning_memory=learning_memory,
        real_operational=real_operational,
        log=lambda event, payload=None: events.append((event, payload or {})),
        events=events,
    )


def test_healthy_runtime_allows_new_tasks_but_never_grants_risk_authority():
    engine = _engine()
    report = SovereignEngine._refresh_health_isolation(engine)

    assert report["state"] == "healthy"
    assert report["allow_new_tasks"] is True
    assert report["allow_risk_bearing_actions"] is False
    assert report["isolate"] is False


def test_enabled_but_unavailable_learning_memory_blocks_new_entries():
    engine = _engine(learning_memory=None)
    report = SovereignEngine._refresh_health_isolation(engine)

    assert report["state"] == "degraded"
    assert report["allow_new_tasks"] is False
    assert report["allow_risk_bearing_actions"] is False
    assert "learning_memory_unavailable:error" in report["reasons"]


def test_disabled_learning_memory_is_not_misclassified_as_failure():
    engine = _engine(learning_enabled=False, learning_memory=None)
    report = SovereignEngine._refresh_health_isolation(engine)

    assert report["state"] == "healthy"
    assert report["allow_new_tasks"] is True


def test_safe_mode_quarantines_new_entries():
    engine = _engine(status="SAFE_MODE")
    report = SovereignEngine._refresh_health_isolation(engine)

    assert report["state"] == "quarantined"
    assert report["isolate"] is True
    assert report["allow_new_tasks"] is False


def test_failed_watchdog_quarantines_new_entries():
    engine = _engine(watchdog={"ok": False, "reason": "network unavailable"})
    report = SovereignEngine._refresh_health_isolation(engine)

    assert report["state"] == "quarantined"
    assert report["allow_new_tasks"] is False
    assert "watchdog_check_failed:critical" in report["reasons"]


def test_non_operational_real_mode_is_quarantined():
    engine = _engine(mode="REAL", real_operational=False)
    report = SovereignEngine._refresh_health_isolation(engine)

    assert report["state"] == "quarantined"
    assert report["allow_new_tasks"] is False
    assert "real_runtime_not_operational:critical" in report["reasons"]


def test_health_transition_is_audited_only_when_decision_changes():
    engine = _engine(learning_memory=None)
    first = SovereignEngine._refresh_health_isolation(engine)
    second = SovereignEngine._refresh_health_isolation(engine)

    assert first["state"] == second["state"] == "degraded"
    assert len(engine.events) == 1
    assert engine.events[0][0] == "HEALTH_ISOLATION_DECISION"


def test_safe_state_transition_refreshes_health_immediately():
    engine = _engine()
    engine._refresh_health_isolation = lambda: SovereignEngine._refresh_health_isolation(engine)

    SovereignEngine._enter_safe_state(engine, "synthetic_test_failure")

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.health_isolation["state"] == "quarantined"
    assert engine.state.health_isolation["allow_new_tasks"] is False


def test_order_entry_boundary_blocks_before_touching_execution_dependencies():
    events = []
    engine = SimpleNamespace(
        state=SimpleNamespace(health_isolation={
            "state": "degraded",
            "allow_new_tasks": False,
            "reasons": ["learning_memory_unavailable:error"],
        }),
        paper=True,
        log=lambda event, payload=None: events.append((event, payload or {})),
    )

    SovereignEngine._open_position(
        engine, None, "BTC/USDT", 100.0, 0.1, 0.02, 0.04, "synthetic"
    )

    assert len(events) == 1
    assert events[0][0] == "HEALTH_ISOLATION_ORDER_BLOCK"
    assert events[0][1]["symbol"] == "BTC/USDT"


def test_fail_safe_health_refresh_supports_partial_recovery_engine_instances():
    from PC_ENGINE.core.engine import RuntimeState

    engine = object.__new__(SovereignEngine)
    engine.state = RuntimeState()
    engine.mode = "PAPER"
    engine.real_operational = False
    engine.learning_memory = None
    engine.log = lambda *args, **kwargs: None

    engine._enter_safe_state("synthetic_recovery_failure")

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.health_isolation["state"] == "quarantined"
    assert engine.state.health_isolation["allow_new_tasks"] is False
