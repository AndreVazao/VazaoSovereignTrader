from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from PC_ENGINE.execution.desktop_paper_surface import (
    DesktopPaperConfig,
    DesktopPaperSurfaceAdapter,
)
from PC_ENGINE.execution.surface_adapters import ActionKind, SurfaceAction, Surface


def test_missing_desktop_executable_is_down(tmp_path: Path) -> None:
    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(
            venue_id="demo",
            executable_path=str(tmp_path / "missing.exe"),
            feedback_path=str(tmp_path / "feedback.jsonl"),
        )
    )

    feedback = adapter.probe()

    assert feedback.surface is Surface.DESKTOP_APP
    assert feedback.state == "DOWN"
    assert feedback.acknowledged is False


def test_paper_trade_intent_never_submits_order(tmp_path: Path) -> None:
    executable = tmp_path / "demo"
    executable.write_text("placeholder", encoding="utf-8")

    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(
            venue_id="demo",
            executable_path=str(executable),
            feedback_path=str(tmp_path / "feedback.jsonl"),
        )
    )

    feedback = adapter.execute(
        SurfaceAction(
            request_id="paper-1",
            venue_id="demo",
            surface=Surface.DESKTOP_APP,
            action=ActionKind.BUY,
            paper_only=False,
        )
    )

    assert feedback.state == "PAPER_INTENT_RECORDED"
    assert feedback.order_reference is None
    snapshot = adapter.feedback_snapshot()
    assert snapshot["execution_authorized"] is False
    assert snapshot["orders_submitted"] is False
    assert snapshot["surfaces"][0]["state"] == "DEGRADED"


def test_connect_launches_only_configured_local_process(tmp_path: Path) -> None:
    executable = Path(sys.executable)
    args = ("-c", "import time; time.sleep(2)")

    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(
            venue_id="demo",
            executable_path=str(executable),
            launch_args=args,
        )
    )

    feedback = adapter.execute(
        SurfaceAction(
            request_id="connect-1",
            venue_id="demo",
            surface=Surface.DESKTOP_APP,
            action=ActionKind.CONNECT,
        )
    )

    assert feedback.state == "CONNECTED"
    assert feedback.acknowledged is True
    adapter._process.terminate()  # type: ignore[union-attr]



def test_connect_reports_fast_exit_as_down(tmp_path: Path) -> None:
    executable = Path(sys.executable)
    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(
            venue_id="demo",
            executable_path=str(executable),
            launch_args=("-c", "raise SystemExit(7)"),
        )
    )

    feedback = adapter.execute(
        SurfaceAction(
            request_id="connect-fast-exit",
            venue_id="demo",
            surface=Surface.DESKTOP_APP,
            action=ActionKind.CONNECT,
        )
    )

    assert feedback.state == "DOWN"
    assert feedback.acknowledged is False
    assert "exit_code=7" in feedback.detail


def test_observe_preserves_request_id_in_persisted_feedback(tmp_path: Path) -> None:
    executable = Path(sys.executable)
    feedback_path = tmp_path / "feedback.jsonl"
    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(
            venue_id="demo",
            executable_path=str(executable),
            launch_args=("-c", "import time; time.sleep(2)"),
            feedback_path=str(feedback_path),
        )
    )
    launched = adapter.execute(
        SurfaceAction(
            request_id="connect-observe",
            venue_id="demo",
            surface=Surface.DESKTOP_APP,
            action=ActionKind.CONNECT,
        )
    )
    assert launched.state == "CONNECTED"

    observed = adapter.execute(
        SurfaceAction(
            request_id="observe-request-42",
            venue_id="demo",
            surface=Surface.DESKTOP_APP,
            action=ActionKind.OBSERVE,
        )
    )

    assert observed.request_id == "observe-request-42"
    stored = feedback_path.read_text(encoding="utf-8")
    assert '"request_id": "observe-request-42"' in stored
    adapter._process.terminate()  # type: ignore[union-attr]


def test_directory_is_not_accepted_as_executable(tmp_path: Path) -> None:
    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(venue_id="demo", executable_path=str(tmp_path))
    )

    feedback = adapter.probe()

    assert feedback.state == "DOWN"
    assert feedback.acknowledged is False


def test_connect_does_not_launch_duplicate_process(tmp_path: Path) -> None:
    executable = Path(sys.executable)
    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(
            venue_id="demo",
            executable_path=str(executable),
            launch_args=("-c", "import time; time.sleep(3)"),
        )
    )
    first = adapter.execute(
        SurfaceAction(
            request_id="connect-once",
            venue_id="demo",
            surface=Surface.DESKTOP_APP,
            action=ActionKind.CONNECT,
        )
    )
    process = adapter._process
    second = adapter.execute(
        SurfaceAction(
            request_id="connect-twice",
            venue_id="demo",
            surface=Surface.DESKTOP_APP,
            action=ActionKind.CONNECT,
        )
    )
    try:
        assert first.state == "CONNECTED"
        assert second.state == "CONNECTED"
        assert "no_duplicate_launch" in second.detail
        assert adapter._process is process
    finally:
        if process is not None and process.poll() is None:
            process.terminate()


def test_window_observation_never_returns_raw_window_title(monkeypatch) -> None:
    class FakeWindow:
        def window_text(self) -> str:
            return "Exchange - account@example.invalid"

    class FakeDesktop:
        def __init__(self, backend: str) -> None:
            assert backend == "uia"

        def windows(self, visible_only: bool) -> list[FakeWindow]:
            assert visible_only is True
            return [FakeWindow()]

    monkeypatch.setitem(
        sys.modules,
        "pywinauto",
        SimpleNamespace(Desktop=FakeDesktop),
    )
    adapter = DesktopPaperSurfaceAdapter(
        DesktopPaperConfig(
            venue_id="demo",
            executable_path=sys.executable,
            window_title_contains="Exchange",
        )
    )

    result = adapter._window_observation()

    assert result == "window_title_match=True"
    assert "account@example.invalid" not in result
