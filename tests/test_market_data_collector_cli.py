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
