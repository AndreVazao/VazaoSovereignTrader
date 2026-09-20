from PC_ENGINE.research.autonomous import AutonomousResearchWorker


def test_autonomous_worker_creates_research_without_message(tmp_path):
    worker = AutonomousResearchWorker(str(tmp_path))
    assert worker.observe("BTC/USDT", 82, "TREND", {"score": 82})
    snap = worker.snapshot()
    assert snap["queue"]["pending"] == 1


def test_autonomous_worker_deduplicates(tmp_path):
    worker = AutonomousResearchWorker(str(tmp_path))
    assert worker.observe("ETH/USDT", 80, "TREND")
    assert not worker.observe("ETH/USDT", 80, "TREND")
