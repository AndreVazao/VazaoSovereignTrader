from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import PC_ENGINE.execution.android_adb_paper_surface as android_module
from PC_ENGINE.execution.android_adb_paper_surface import AndroidAdbConfig, AndroidAdbPaperSurfaceAdapter
from PC_ENGINE.execution.surface_adapters import ActionKind, Surface, SurfaceAction


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _adapter(tmp_path: Path, **kwargs) -> AndroidAdbPaperSurfaceAdapter:
    return AndroidAdbPaperSurfaceAdapter(
        AndroidAdbConfig(venue_id="demo", feedback_path=str(tmp_path / "feedback.jsonl"), **kwargs)
    )


def _mock_adb(monkeypatch, responses):
    monkeypatch.setattr(android_module.shutil, "which", lambda _: "/usr/bin/adb")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs.get("shell") is False
        result = responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    monkeypatch.setattr(android_module.subprocess, "run", run)
    return calls


def test_adb_unavailable_is_explicit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(android_module.shutil, "which", lambda _: None)
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "ADB_UNAVAILABLE"
    assert feedback.acknowledged is False


def test_no_connected_devices(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("Android Debug Bridge version 1.0.41"), _completed("List of devices attached\n\n")])
    feedback = _adapter(tmp_path).observe()
    assert feedback.state == "NO_DEVICE"
    assert feedback.acknowledged is False


def test_unauthorized_device_is_not_reported_connected(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("version"), _completed("List of devices attached\nemulator-5554 unauthorized\n")])
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "DEVICE_UNAUTHORIZED"
    assert feedback.acknowledged is False


def test_offline_device_is_reported(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("version"), _completed("List of devices attached\nemulator-5554 offline\n")])
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "DEVICE_OFFLINE"


def test_no_permissions_state_is_not_malformed(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("version"), _completed("List of devices attached\nphone123 no permissions (user in plugdev group)\n")])
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "DEVICE_UNAUTHORIZED"


def test_malformed_devices_output_is_communication_error(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("version"), _completed("unexpected output")])
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "COMMUNICATION_ERROR"
    assert "malformed_output" in feedback.detail


def test_adb_timeout_is_reported(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("version"), subprocess.TimeoutExpired(["adb", "devices"], 5)])
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "COMMUNICATION_ERROR"
    assert feedback.detail == "adb_devices_timeout"


def test_connected_device_without_package_is_apk_not_configured(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("version"), _completed("List of devices attached\nemulator-5554 device product:sdk\n")])
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "APK_NOT_CONFIGURED"
    assert feedback.acknowledged is True
    assert "package_name_not_configured" in feedback.detail


def test_package_process_not_observed_is_explicit(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [
        _completed("version"),
        _completed("List of devices attached\nemulator-5554 device\n"),
        _completed("", returncode=1),
    ])
    feedback = _adapter(tmp_path, package_name="com.example.paper").probe()
    assert feedback.state == "APP_NOT_OBSERVED"
    assert feedback.acknowledged is False


def test_package_process_observed_is_operational_only(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [
        _completed("version"),
        _completed("List of devices attached\nemulator-5554 device\n"),
        _completed("1234\n"),
    ])
    feedback = _adapter(tmp_path, package_name="com.example.paper").probe()
    assert feedback.state == "APP_OBSERVED"
    assert feedback.order_reference is None


def test_multiple_devices_requires_explicit_selection(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [
        _completed("version"),
        _completed("List of devices attached\nemulator-5554 device\nphone123 device\n"),
    ])
    feedback = _adapter(tmp_path).probe()
    assert feedback.state == "MULTIPLE_DEVICES"
    assert "configure_device_serial" in feedback.detail


def test_paper_trade_intent_never_calls_adb(tmp_path: Path, monkeypatch) -> None:
    def unexpected_run(*args, **kwargs):
        raise AssertionError("PAPER trade intent must not invoke ADB")

    monkeypatch.setattr(android_module.subprocess, "run", unexpected_run)
    adapter = _adapter(tmp_path)
    feedback = adapter.execute(
        SurfaceAction("paper-android-1", "demo", Surface.ANDROID_APK, ActionKind.BUY, paper_only=False)
    )
    assert feedback.state == "PAPER_INTENT_RECORDED"
    assert "no_android_ui_interaction" in feedback.detail
    assert "no_order_submitted" in feedback.detail
    assert adapter.feedback_snapshot()["execution_authorized"] is False


def test_connect_and_observe_preserve_request_id_in_persistent_feedback(tmp_path: Path, monkeypatch) -> None:
    _mock_adb(monkeypatch, [_completed("version"), _completed("List of devices attached\n\n")])
    adapter = _adapter(tmp_path)
    feedback = adapter.execute(
        SurfaceAction("request-android-42", "demo", Surface.ANDROID_APK, ActionKind.OBSERVE)
    )
    assert feedback.request_id == "request-android-42"
    stored = (tmp_path / "feedback.jsonl").read_text(encoding="utf-8")
    assert '"request_id": "request-android-42"' in stored
    assert '"execution_authorized": false' in stored
