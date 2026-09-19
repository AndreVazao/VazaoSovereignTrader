import json

from PC_ENGINE.autonomy.paper_reconciliation import PaperAutonomyReconciler


def test_reconciles_filled_partial_and_missing(tmp_path):
    intents = tmp_path / "intents.jsonl"
    fills = tmp_path / "fills.jsonl"
    runs = tmp_path / "runs.jsonl"
    output = tmp_path / "report.json"

    intents.write_text(
        "\n".join([
            json.dumps({"intent_id": "i1", "opportunity_id": "o1", "venue": "binance", "symbol": "BTC/USDT", "side": "BUY", "required_capital": 100}),
            json.dumps({"intent_id": "i2", "opportunity_id": "o2", "venue": "okx", "symbol": "ETH/USDT", "side": "SELL", "required_capital": 50}),
            json.dumps({"intent_id": "i3", "opportunity_id": "o3", "venue": "okx", "symbol": "SOL/USDT", "side": "BUY", "required_capital": 25}),
        ]) + "\n",
        encoding="utf-8",
    )
    fills.write_text(
        "\n".join([
            json.dumps({"fill_id": "f1", "opportunity_id": "o1", "requested_qty": 1, "filled_qty": 1, "fill_price": 100, "fee": 0.1, "status": "FILLED"}),
            json.dumps({"fill_id": "f2", "opportunity_id": "o2", "requested_qty": 2, "filled_qty": 1, "fill_price": 50, "fee": 0.05, "status": "PARTIAL"}),
        ]) + "\n",
        encoding="utf-8",
    )
    runs.write_text(json.dumps({"run_id": "r1", "gross_pnl": 3, "fees": 0.2, "net_pnl": 2.8}) + "\n", encoding="utf-8")

    report = PaperAutonomyReconciler(str(intents), str(fills), str(runs), str(output)).reconcile()

    assert report["intents"] == 3
    assert report["completed_intents"] == 1
    assert report["partial_intents"] == 1
    assert report["missing_intents"] == 1
    assert report["net_pnl"] == 2.8
    assert output.exists()
