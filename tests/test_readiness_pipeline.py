from PC_ENGINE.tools.run_readiness_pipeline import run_execution_smoke_test


def test_paper_execution_smoke_test_passes():
    result = run_execution_smoke_test()
    assert result["paper_only"] is True
    assert result["ok"] is True
    assert all(result["checks"].values())
