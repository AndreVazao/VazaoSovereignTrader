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
