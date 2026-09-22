from __future__ import annotations

import json

from PC_ENGINE.autonomy.paper_orchestrator import PaperAutonomyOrchestrator


def test_only_stable_oos_evidence_becomes_intent(tmp_path):
    validation = tmp_path / "validation.json"
    replay = tmp_path / "replay.json"
    output = tmp_path / "intents.jsonl"
    validation.write_text(json.dumps({
        "rows": [
            {
                "leader": "A", "follower": "B", "symbol": "BTC/USDT", "direction": "UP",
                "in_expectancy": 2.0, "out_expectancy": 3.0,
                "out_ci_low": 2.95, "out_ci_high": 3.05,
                "out_completion_rate": 1.0,
                "out_average_entry_impact_bps": 2.0,
                "out_average_exit_impact_bps": 2.0,
                "stable": True,
            },
            {
                "leader": "C", "follower": "D", "symbol": "ETH/USDT", "direction": "UP",
                "in_expectancy": 4.0, "out_expectancy": 0.5,
                "out_ci_low": -2.0, "out_ci_high": 3.0,
                "out_completion_rate": 1.0,
                "stable": False,
            },
        ]
    }), encoding="utf-8")
    replay.write_text(json.dumps({"trades": []}), encoding="utf-8")
    rows = PaperAutonomyOrchestrator(
        str(validation), str(replay), str(output)
    ).run(available_capital=1000, max_exposure=350)
    assert len(rows) == 1
    assert rows[0]["paper"] is True
    assert output.exists()
