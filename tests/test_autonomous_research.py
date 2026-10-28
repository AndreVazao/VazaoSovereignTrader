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

def test_autonomous_worker_persists_unverified_observation_to_durable_memory(tmp_path):
    from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory

    database = tmp_path / "learning.sqlite3"
    research_dir = tmp_path / "research"
    with SQLiteLearningMemory(database) as memory:
        worker = AutonomousResearchWorker(str(research_dir), learning_memory=memory)
        assert worker.observe("BTC/USDT", 82, "TREND", {"score": 82, "paper_only": True})

        records = memory.list_records()
        assert len(records) == 1
        record = records[0]
        assert record.department == "market_radar"
        assert record.status == "unverified"
        assert record.confidence == 0.82
        assert record.value["symbol"] == "BTC/USDT"
        assert record.value["opportunity"] == {"score": 82, "paper_only": True}
        assert record.provenance.startswith("autonomous_observation:")
        assert worker.snapshot()["durable_memory"] == {
            "enabled": True,
            "write_failures": 0,
            "last_error": "",
        }


def test_autonomous_worker_survives_durable_memory_write_failure(tmp_path):
    class FailingMemory:
        def put(self, **_kwargs):
            raise OSError("disk unavailable")

    worker = AutonomousResearchWorker(str(tmp_path), learning_memory=FailingMemory())
    assert worker.observe("ETH/USDT", 80, "TREND")
    snapshot = worker.snapshot()
    assert snapshot["queue"]["pending"] == 1
    assert snapshot["durable_memory"]["write_failures"] == 1
    assert snapshot["durable_memory"]["last_error"] == "OSError"

