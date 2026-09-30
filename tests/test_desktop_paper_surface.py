from __future__ import annotations

import sys
from pathlib import Path

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
    assert snapshot["surfaces"][0]["state"] == "HEALTHY"


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
