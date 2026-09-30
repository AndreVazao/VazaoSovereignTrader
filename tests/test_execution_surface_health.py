from PC_ENGINE.execution.surface_health import (
    ExecutionSurface,
    SurfaceState,
    classify_surface,
    snapshot,
)


def test_web_browser_surface_is_healthy_when_recent_feedback_exists():
    status = classify_surface(
        venue_id="example-web",
        account_id="paper",
        surface=ExecutionSurface.WEB_BROWSER,
        enabled=True,
        check_ok=True,
        feedback_age_ms=500,
    )
    assert status.state is SurfaceState.HEALTHY
    assert status.paper_only is True
    assert status.execution_authorized is False


def test_android_surface_degrades_when_feedback_is_stale():
    status = classify_surface(
        venue_id="example-mobile",
        account_id="paper",
        surface=ExecutionSurface.ANDROID_APK,
        enabled=True,
        check_ok=True,
        feedback_age_ms=31_000,
        stale_after_ms=30_000,
    )
    assert status.state is SurfaceState.DEGRADED


def test_desktop_app_is_down_when_probe_fails():
    status = classify_surface(
        venue_id="example-desktop",
        account_id="paper",
        surface=ExecutionSurface.DESKTOP_APP,
        enabled=True,
        check_ok=False,
        feedback_age_ms=100,
    )
    assert status.state is SurfaceState.DOWN


def test_unconfigured_surface_is_explicit():
    status = classify_surface(
        venue_id="example",
        account_id="paper",
        surface=ExecutionSurface.ANDROID_APK,
        enabled=False,
        check_ok=None,
        feedback_age_ms=None,
    )
    assert status.state is SurfaceState.NOT_CONFIGURED


def test_snapshot_never_authorizes_execution():
    result = snapshot(
        [
            classify_surface(
                venue_id="example",
                account_id="paper",
                surface=ExecutionSurface.WEB_BROWSER,
                enabled=True,
                check_ok=True,
                feedback_age_ms=100,
            )
        ]
    )
    assert result["operational_only"] is True
    assert result["paper_only"] is True
    assert result["orders_submitted"] is False
    assert result["execution_authorized"] is False
