from __future__ import annotations

import pytest

from PC_ENGINE.tools.run_market_data_collector import _build_parser


def test_market_data_collector_defaults_to_continuous_mode() -> None:
    args = _build_parser().parse_args([])
    assert args.run_seconds == 0.0


def test_market_data_collector_accepts_bounded_graceful_run() -> None:
    args = _build_parser().parse_args(["--run-seconds", "15"])
    assert args.run_seconds == 15.0


def test_market_data_collector_rejects_negative_run_duration() -> None:
    args = _build_parser().parse_args(["--run-seconds", "-1"])
    assert args.run_seconds == -1.0
    with pytest.raises(SystemExit):
        from PC_ENGINE.tools.run_market_data_collector import main

        main(["--run-seconds", "-1"])


def test_frozen_collector_resolves_relative_paths_from_executable_directory(monkeypatch, tmp_path) -> None:
    import sys

    from PC_ENGINE.tools import run_market_data_collector as collector

    executable = tmp_path / "VazaoSovereignTrader-MarketData.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(collector, "REPO_ROOT", collector._runtime_root())

    assert collector._resolve_path("config/config.local.json") == tmp_path / "config" / "config.local.json"
    assert collector._resolve_path("data/radar") == tmp_path / "data" / "radar"
