from PC_ENGINE.research.worker import ResearchWorker


def test_worker_discards_inaccessible_source(tmp_path):
    w = ResearchWorker(str(tmp_path), timeout_seconds=0.01)
    req = w.inbox.submit("investigate https://127.0.0.1:9/nope")
    result = w.process_pending()
    assert result["processed"] == 1
    latest = w.inbox._latest()[req.request_id]
    assert latest.status == "DISCARDED"


def test_worker_is_non_trading():
    assert not hasattr(ResearchWorker, "execute_order")
