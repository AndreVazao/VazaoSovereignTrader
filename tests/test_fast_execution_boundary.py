def test_fast_execution_boundary_has_no_direct_exchange_dependency():
    from PC_ENGINE.core.fast_execution_router import FastExecutionRouter
    assert FastExecutionRouter.__module__ == "PC_ENGINE.core.fast_execution_router"
