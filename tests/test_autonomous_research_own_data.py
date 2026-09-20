import json

from PC_ENGINE.research.worker import ResearchWorker


def test_autonomous_request_without_url_is_evaluated(tmp_path):
    replay = tmp_path / "replay.json"
    oos = tmp_path / "oos.json"
    replay.write_text(json.dumps({"trades": []}), encoding="utf-8")
    oos.write_text(json.dumps({"rows": []}), encoding="utf-8")
    worker = ResearchWorker(str(tmp_path))
    worker.evaluator.replay_path = replay
    worker.evaluator.oos_path = oos
    request = worker.inbox.submit("Investigar autonomamente BTC no regime TREND")
    result = worker.process_pending()
    latest = worker.inbox._latest()[request.request_id]
    assert result["processed"] == 1
    assert latest.status == "COMPLETED"
    assert "dados próprios" in latest.result.lower()
