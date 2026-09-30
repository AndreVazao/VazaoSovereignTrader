from __future__ import annotations

import json

from PC_ENGINE.diagnostics.evidence_scorecard import refresh_runtime_evidence_reports


def test_refresh_generates_paper_reports_without_authorizing_execution(tmp_path):
    report = refresh_runtime_evidence_reports({
        "radar": {
            "data_dir": str(tmp_path),
            "hot_path_outcomes_path": str(tmp_path / "missing_outcomes.jsonl"),
            "evidence_train_size": 4,
            "evidence_test_size": 2,
            "evidence_min_test_samples": 2,
        }
    })

    assert report["outcomes_file_exists"] is False
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert report["scorecard"]["execution_authorized"] is False
    assert "venue_economic_evidence" in report["reports"]
    assert report["reports"]["venue_economic_evidence"]["execution_authorized"] is False
    for name, filename in (
        ("calibration", "hot_path_calibration.json"),
        ("walk_forward", "hot_path_walk_forward.json"),
        ("regime_walk_forward", "hot_path_regime_walk_forward.json"),
        ("oos_robustness", "hot_path_oos_robustness.json"),
        ("relationship_oos", "hot_path_relationship_oos.json"),
    ):
        path = tmp_path / filename
        assert path.exists(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["paper_only"] is True
        assert payload["orders_submitted"] is False
        assert payload["execution_authorized"] is False



def test_relative_configured_paths_resolve_from_repository_root(tmp_path, monkeypatch):
    from PC_ENGINE.diagnostics import path_utils

    monkeypatch.setattr(path_utils, "REPO_ROOT", tmp_path)
    report = refresh_runtime_evidence_reports({
        "radar": {
            "data_dir": "runtime/radar",
            "hot_path_outcomes_path": "runtime/custom-outcomes.jsonl",
            "evidence_reports": {"calibration": "reports/custom-calibration.json"},
            "evidence_train_size": 4,
            "evidence_test_size": 2,
            "evidence_min_test_samples": 2,
        }
    })

    assert report["outcomes_path"] == str(tmp_path / "runtime/custom-outcomes.jsonl")
    assert report["outcomes_file_exists"] is False
    assert (tmp_path / "reports/custom-calibration.json").is_file()
    assert (tmp_path / "runtime/radar/hot_path_walk_forward.json").is_file()
    assert report["scorecard"]["report_paths"]["calibration"] == str(tmp_path / "reports/custom-calibration.json")


def test_collector_honours_configured_outcomes_path(tmp_path, monkeypatch):
    from PC_ENGINE.tools import run_market_data_collector as collector

    monkeypatch.setattr(collector, "REPO_ROOT", tmp_path)
    radar_cfg = {"hot_path_outcomes_path": "runtime/custom-outcomes.jsonl"}
    data_dir = tmp_path / "runtime" / "radar"

    assert collector._outcomes_path(radar_cfg, data_dir) == tmp_path / "runtime/custom-outcomes.jsonl"
    assert collector._outcomes_path({}, data_dir) == data_dir / "hot_path_outcomes.jsonl"


def test_refresh_survives_corrupt_utf8_and_json_lines_in_outcomes(tmp_path):
    outcomes = tmp_path / "corrupt-outcomes.jsonl"
    outcomes.write_bytes(b"\xff\xfe\n{bad json\n")
    result = refresh_runtime_evidence_reports({
        "radar": {
            "data_dir": str(tmp_path),
            "hot_path_outcomes_path": str(outcomes),
            "evidence_train_size": 2,
            "evidence_test_size": 2,
            "evidence_min_test_samples": 2,
        }
    })
    assert result["outcomes_file_exists"] is True
    assert result["paper_only"] is True
    assert result["execution_authorized"] is False
    assert result["reports"]["calibration"]["outcome_samples"] == 0
    assert result["reports"]["walk_forward"]["timestamped_valid_records"] == 0


def test_refresh_generates_relationship_oos_report_from_completed_paper_outcomes(tmp_path):
    outcomes = tmp_path / "hot_path_outcomes.jsonl"
    rows = []
    for i in range(10):
        rows.append({
            "status": "COMPLETED",
            "paper_only": True,
            "orders_submitted": False,
            "outcome_id": f"refresh-{i}",
            "symbol": "BTC/USDT",
            "leader": "binance",
            "follower": "coinbase",
            "direction": "UP",
            "horizon_ms": 500,
            "expected_net_bps": 1.0,
            "realized_net_bps": -1.0 if i < 7 else 2.0,
            "outcome_local_ts_ms": 1_000 + i * 1_000,
        })
    outcomes.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    result = refresh_runtime_evidence_reports({
        "radar": {
            "data_dir": str(tmp_path),
            "hot_path_outcomes_path": str(outcomes),
            "evidence_train_size": 4,
            "evidence_test_size": 2,
            "evidence_min_test_samples": 2,
            "evidence_relationship_min_samples": 10,
            "evidence_relationship_min_test_samples": 3,
        }
    })

    report = result["reports"]["relationship_oos"]
    saved = tmp_path / "hot_path_relationship_oos.json"
    assert saved.is_file()
    assert json.loads(saved.read_text(encoding="utf-8"))["relationships"] == 1
    assert report["valid_unique_outcomes"] == 10
    assert report["relationship_details"][0]["train_end_ms"] < report["relationship_details"][0]["test_start_ms"]
    assert result["scorecard"]["execution_authorized"] is False
    assert result["execution_authorized"] is False



def test_collector_append_path_is_consumed_by_explicit_evidence_refresh(tmp_path, monkeypatch):
    import time
    from pathlib import Path

    from PC_ENGINE.diagnostics import path_utils
    from PC_ENGINE.radar.hot_path_persistence import append_paper_outcomes
    from PC_ENGINE.tools import run_market_data_collector as collector

    monkeypatch.setattr(collector, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(path_utils, "REPO_ROOT", tmp_path)

    radar_config = {
        "data_dir": "runtime/radar",
        "hot_path_outcomes_path": "runtime/custom-outcomes.jsonl",
        "evidence_train_size": 4,
        "evidence_test_size": 2,
        "evidence_min_test_samples": 2,
        "evidence_relationship_min_samples": 10,
        "evidence_relationship_min_test_samples": 3,
        "websocket_exchanges": ["coinbase"],
        "top_of_book_min_samples": 2,
        "top_of_book_max_age_ms": 30_000,
    }
    collector_data_dir = collector._resolve_path(radar_config["data_dir"])
    collector_path = collector._outcomes_path(radar_config, collector_data_dir)
    refresh_path = path_utils.resolve_config_path(radar_config["hot_path_outcomes_path"])
    assert collector_path == refresh_path

    now_ms = time.time_ns() // 1_000_000
    outcomes = [
        {
            "status": "COMPLETED",
            "paper_only": True,
            "orders_submitted": False,
            "outcome_id": f"integration-{i}",
            "symbol": "BTC/USDT",
            "leader": "binance",
            "follower": "coinbase",
            "direction": "UP",
            "horizon_ms": 500,
            "expected_net_bps": 1.0,
            "realized_net_bps": -1.0 if i < 8 else 2.0,
            "outcome_local_ts_ms": now_ms - (20 - i) * 1_000,
        }
        for i in range(12)
    ]

    assert append_paper_outcomes(collector_path, outcomes) == len(outcomes)
    assert collector_path.is_file()

    ticker_path = collector_data_dir / "websocket_ticker_events.jsonl"
    ticker_path.parent.mkdir(parents=True, exist_ok=True)
    ticker_rows = [
        {
            "event_id": f"ticker-{i}",
            "venue": "coinbase",
            "symbol": "BTC/USDT",
            "event_type": "ticker",
            "bid": 100.0 + i * 0.1,
            "ask": 100.2 + i * 0.1,
            "local_receive_wall_ns": now_ms * 1_000_000,
            "observation_type": "PUBLIC_TOP_OF_BOOK",
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
        }
        for i in range(2)
    ]
    ticker_path.write_text("\n".join(json.dumps(row) for row in ticker_rows) + "\n", encoding="utf-8")

    result = refresh_runtime_evidence_reports({"radar": radar_config})
    relationship_report = result["reports"]["relationship_oos"]
    report_path = tmp_path / "runtime" / "radar" / "hot_path_relationship_oos.json"

    assert Path(result["outcomes_path"]) == collector_path
    assert result["outcomes_file_exists"] is True
    assert relationship_report["source"] == collector_path.name
    assert relationship_report["raw_lines_seen"] == len(outcomes)
    assert relationship_report["valid_unique_outcomes"] == len(outcomes)
    assert relationship_report["relationships"] == 1
    assert report_path.is_file()
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["valid_unique_outcomes"] == len(outcomes)
    assert saved["execution_authorized"] is False
    assert result["reports"]["venue_economic_evidence"]["paper_only"] is True
    economics_path = tmp_path / "runtime" / "radar" / "venue_economic_evidence.json"
    assert economics_path.is_file()
    economics = json.loads(economics_path.read_text(encoding="utf-8"))
    assert economics["execution_authorized"] is False
    coinbase = next(row for row in economics["venues"] if row["venue"] == "coinbase")
    assert coinbase["spread_status"] == "AVAILABLE"
    assert coinbase["spread_samples"] == 2
    assert coinbase["spread_bps"] > 0
    assert result["execution_authorized"] is False
