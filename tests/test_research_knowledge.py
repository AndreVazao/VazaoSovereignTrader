from PC_ENGINE.research.knowledge import ResearchKnowledge


def test_knowledge_records_and_searches(tmp_path):
    k = ResearchKnowledge(str(tmp_path))
    row = k.record(title="BTC lead lag", category="lead_lag", status="hypothesis",
                   evidence="Observed persistent timing difference", tags=["btc"])
    assert row["category"] == "lead_lag"
    assert len(k.search("timing")) == 1
    assert k.snapshot()["count"] == 1


def test_unknown_category_is_safe(tmp_path):
    k = ResearchKnowledge(str(tmp_path))
    row = k.record(title="x", category="unknown", status="failed", evidence="x")
    assert row["category"] == "market_pattern"
