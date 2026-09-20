from PC_ENGINE.tools.run_readiness_pipeline import run_execution_smoke_test


def test_paper_execution_smoke_test_passes():
    result = run_execution_smoke_test()
    assert result["paper_only"] is True
    assert result["ok"] is True
    assert all(result["checks"].values())


def test_validation_coverage_requires_every_slice_to_pass():
    from PC_ENGINE.tools.run_readiness_pipeline import _all_validation_rows_passed

    assert _all_validation_rows_passed([{"passed": True}, {"passed": True}]) is True
    assert _all_validation_rows_passed([{"passed": True}, {"passed": False}]) is False
    assert _all_validation_rows_passed([]) is False
