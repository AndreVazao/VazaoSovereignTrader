from PC_ENGINE.core.readiness_timeline import ReadinessDiagnosticTimeline


def _rows(states, start=1_000_000, step=60_000):
    names = ReadinessDiagnosticTimeline.COMPONENTS
    rows = []
    for i, state in enumerate(states):
        rows.append({
            "timestamp_ms": start + i * step,
            "status": "READY" if state == "PASS" else "LOCKED",
            "ready": state == "PASS",
            "blockers": [] if state == "PASS" else ["component"],
            "paper_review": {
                "items": [
                    {"name": name, "status": state, "detail": f"{name.lower()} {state.lower()}"}
                    for name in names
                ]
            },
        })
    return rows


def test_timeline_detects_component_transition_and_duration():
    rows = _rows(["PASS", "PASS", "BLOCKED", "BLOCKED", "PASS"])
    result = ReadinessDiagnosticTimeline().analyze(rows)
    base_events = [event for event in result.events if event.component == "BASE"]
    assert [(event.from_status, event.to_status, event.direction) for event in base_events] == [
        ("PASS", "BLOCKED", "DEGRADING"),
        ("BLOCKED", "PASS", "RECOVERING"),
    ]
    assert base_events[0].duration_ms == 60_000
    assert base_events[1].duration_ms == 120_000


def test_timeline_is_deterministic_and_chronological():
    rows = list(reversed(_rows(["PASS", "BLOCKED", "PASS"])))
    first = ReadinessDiagnosticTimeline(max_events=50).analyze(rows).to_dict()
    second = ReadinessDiagnosticTimeline(max_events=50).analyze(rows).to_dict()
    assert first == second
    timestamps = [event["timestamp_ms"] for event in first["events"]]
    assert timestamps == sorted(timestamps)


def test_timeline_query_filters_and_limits():
    rows = _rows(["PASS", "BLOCKED", "PASS", "BLOCKED"])
    result = ReadinessDiagnosticTimeline().query(
        rows, component="base", direction="degrading", limit=1
    )
    assert result["returned_events"] == 1
    assert result["events"][0]["component"] == "BASE"
    assert result["events"][0]["direction"] == "DEGRADING"


def test_timeline_fails_closed_on_duplicate_timestamps():
    rows = _rows(["PASS", "BLOCKED", "PASS"])
    rows[2]["timestamp_ms"] = rows[1]["timestamp_ms"]
    result = ReadinessDiagnosticTimeline().analyze(rows)
    assert result.status == "INVALID_HISTORY"


def test_timeline_fails_closed_on_missing_component():
    rows = _rows(["PASS", "BLOCKED"])
    rows[1]["paper_review"]["items"] = rows[1]["paper_review"]["items"][:-1]
    result = ReadinessDiagnosticTimeline().analyze(rows)
    assert result.status == "INVALID_HISTORY"


def test_timeline_empty_history_is_insufficient():
    result = ReadinessDiagnosticTimeline().analyze([])
    assert result.status == "INSUFFICIENT_HISTORY"
    assert result.to_dict()["paper_only"] is True
