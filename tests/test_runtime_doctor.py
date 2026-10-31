from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from PC_ENGINE.tools.doctor import collect_diagnostics


def write_config(root: Path, content: str, *, local: bool = False) -> Path:
    config_dir = root / "PC_ENGINE" / "config"
    config_dir.mkdir(parents=True)
    path = config_dir / ("config.local.json" if local else "config.example.json")
    path.write_text(content, encoding="utf-8")
    return path


def test_doctor_is_read_only_and_reports_capabilities(tmp_path: Path):
    write_config(tmp_path, json.dumps({"mode": "PAPER", "private_secret": "must-not-leak"}))
    dependencies = {name: object() for name in ("flask", "ccxt", "playwright")}
    with patch("PC_ENGINE.tools.doctor.importlib.util.find_spec", side_effect=lambda name: dependencies.get(name)):
        report = collect_diagnostics(tmp_path)

    assert report["read_only"] is True
    assert report["changes_made"] is False
    assert report["network_requests"] == 0
    assert report["safety"]["effective_mode"] == "PAPER"
    assert report["checks"]["config"]["ok"] is True
    assert report["checks"]["dependencies"]["ok"] is True
    assert report["status"] == "READY"
    assert "private_secret" not in json.dumps(report)
    assert not (tmp_path / "PC_ENGINE" / "data").exists()


def test_doctor_never_promotes_real_config(tmp_path: Path):
    write_config(tmp_path, json.dumps({"mode": "REAL"}), local=True)
    report = collect_diagnostics(tmp_path)
    assert report["status"] == "SAFE_STATE"
    assert report["safety"]["configured_mode"] == "REAL"
    assert report["safety"]["effective_mode"] == "PAPER"
    assert report["safety"]["real_promotion_attempted"] is False


def test_doctor_reports_invalid_config_without_echoing_contents(tmp_path: Path):
    write_config(tmp_path, '{"token":"do-not-print", invalid json')
    report = collect_diagnostics(tmp_path)
    rendered = json.dumps(report)
    assert report["status"] == "DEGRADED"
    assert report["checks"]["config"]["ok"] is False
    assert "do-not-print" not in rendered


def test_doctor_does_not_create_missing_config_or_data_dirs(tmp_path: Path):
    report = collect_diagnostics(tmp_path)
    assert report["status"] == "DEGRADED"
    assert report["checks"]["config"]["ok"] is False
    assert not (tmp_path / "PC_ENGINE" / "config").exists()
    assert not (tmp_path / "PC_ENGINE" / "data").exists()



def test_visual_profile_keeps_lightweight_modes_available_without_renderer_probe(tmp_path: Path):
    write_config(tmp_path, json.dumps({"mode": "PAPER"}))
    with patch("PC_ENGINE.tools.doctor._available_ram_bytes", return_value=16 * 1024**3), patch(
        "PC_ENGINE.tools.doctor.os.cpu_count", return_value=8
    ), patch("PC_ENGINE.tools.doctor._probe_webgl") as probe:
        report = collect_diagnostics(tmp_path)

    probe.assert_not_called()
    assert report["renderer"]["status"] == "not_requested"
    assert report["visual_profile"]["recommended_modes"]["chat"] is True
    assert report["visual_profile"]["recommended_modes"]["pixel"] is True
    assert report["visual_profile"]["recommended_modes"]["enhanced"] is False
    assert report["visual_profile"]["recommended_modes"]["3d"] is False


def test_visual_profile_allows_enhanced_but_not_3d_on_detected_software_renderer(tmp_path: Path):
    write_config(tmp_path, json.dumps({"mode": "PAPER"}))
    renderer = {
        "status": "probed",
        "webgl1": True,
        "webgl2": True,
        "renderer": "SwiftShader",
        "software_renderer_detected": True,
    }
    with patch("PC_ENGINE.tools.doctor._available_ram_bytes", return_value=16 * 1024**3), patch(
        "PC_ENGINE.tools.doctor.os.cpu_count", return_value=8
    ), patch("PC_ENGINE.tools.doctor._probe_webgl", return_value=renderer):
        report = collect_diagnostics(tmp_path, probe_renderer=True)

    assert report["renderer"] == renderer
    assert report["visual_profile"]["recommended_modes"]["chat"] is True
    assert report["visual_profile"]["recommended_modes"]["pixel"] is True
    assert report["visual_profile"]["recommended_modes"]["enhanced"] is True
    assert report["visual_profile"]["recommended_modes"]["3d"] is False
    assert report["network_requests"] == 0
    assert report["changes_made"] is False


def test_visual_profile_enables_3d_only_with_webgl2_and_nonsoftware_renderer(tmp_path: Path):
    write_config(tmp_path, json.dumps({"mode": "PAPER"}))
    renderer = {
        "status": "probed",
        "webgl1": True,
        "webgl2": True,
        "renderer": "Example Hardware Renderer",
        "software_renderer_detected": False,
    }
    with patch("PC_ENGINE.tools.doctor._available_ram_bytes", return_value=16 * 1024**3), patch(
        "PC_ENGINE.tools.doctor.os.cpu_count", return_value=8
    ), patch("PC_ENGINE.tools.doctor._probe_webgl", return_value=renderer):
        report = collect_diagnostics(tmp_path, probe_renderer=True)

    assert report["visual_profile"]["recommended_modes"]["3d"] is True


def test_renderer_probe_failure_is_unknown_and_does_not_echo_exception(tmp_path: Path):
    write_config(tmp_path, json.dumps({"mode": "PAPER"}))
    with patch("PC_ENGINE.tools.doctor.importlib.util.find_spec", return_value=object()), patch(
        "PC_ENGINE.tools.doctor._available_ram_bytes", return_value=16 * 1024**3
    ), patch("PC_ENGINE.tools.doctor.os.cpu_count", return_value=8), patch(
        "PC_ENGINE.tools.doctor._probe_webgl",
        return_value={"status": "unknown", "reason": "BrowserTypeLaunchError", "webgl1": False, "webgl2": False},
    ):
        report = collect_diagnostics(tmp_path, probe_renderer=True)

    assert report["renderer"]["status"] == "unknown"
    assert report["visual_profile"]["recommended_modes"]["3d"] is False
    assert "private" not in json.dumps(report).lower()
