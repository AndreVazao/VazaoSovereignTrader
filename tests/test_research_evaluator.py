import json

from PC_ENGINE.research.evaluator import ResearchOwnDataEvaluator


def test_evaluator_reports_insufficient_data(tmp_path):
    replay = tmp_path / "replay.json"
    oos = tmp_path / "oos.json"
    replay.write_text(json.dumps({"trades": []}), encoding="utf-8")
    oos.write_text(json.dumps({"rows": []}), encoding="utf-8")
    result = ResearchOwnDataEvaluator(str(replay), str(oos)).evaluate("investigar BTC")
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["metrics"]["replay_samples"] == 0


def test_evaluator_matches_symbol_and_detects_stable_oos(tmp_path):
    replay = tmp_path / "replay.json"
    oos = tmp_path / "oos.json"
    trades = [
        {
            "trade_id": str(i),
            "symbol": "BTC/USDT",
            "status": "COMPLETED",
            "exit_filled_qty": 1,
            "net_pnl": 0.5 + i * 0.01,
            "entry_impact_bps": 1.0,
            "exit_impact_bps": 1.0,
        }
        for i in range(6)
    ]
    replay.write_text(json.dumps({"trades": trades}), encoding="utf-8")
    oos.write_text(json.dumps({"rows": [{"symbol": "BTC/USDT", "stable": True}]}), encoding="utf-8")
    result = ResearchOwnDataEvaluator(str(replay), str(oos)).evaluate("investigar BTC")
    assert result["status"] == "OOS_VALIDATION_CANDIDATE"
    assert result["metrics"]["completed_samples"] == 6
    assert result["metrics"]["relevant_stable_oos_rows"] == 1
