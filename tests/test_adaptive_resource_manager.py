from PC_ENGINE.core.adaptive_resource_manager import (
    AdaptiveResourceManager,
    ResourceSnapshot,
    derive_resource_policy,
)


def snapshot(cpu=2, total=3072, available=900, disk=100000, load=20):
    return ResourceSnapshot(cpu, total, available, disk, load, "Windows", 1.0)


def test_low_memory_machine_uses_compact_and_defers_heavy_jobs():
    policy = derive_resource_policy(snapshot())
    assert policy.profile == "COMPACT"
    assert policy.max_workers == 1
    assert policy.max_backtest_workers == 0
    assert policy.max_simulation_workers == 0
    assert policy.defer_heavy_jobs


def test_powerful_machine_scales_parallel_research():
    policy = derive_resource_policy(snapshot(cpu=16, total=32768, available=24000))
    assert policy.profile == "PERFORMANCE"
    assert policy.max_workers > 4
    assert policy.max_backtest_workers > 0
    assert not policy.defer_heavy_jobs


def test_high_load_temporarily_throttles_even_powerful_machine():
    policy = derive_resource_policy(snapshot(cpu=16, total=32768, available=20000, load=96))
    assert policy.profile == "COMPACT"
    assert policy.max_backtest_workers == 0
    assert "high_cpu_load" in policy.reasons


def test_worker_cap_is_respected():
    policy = derive_resource_policy(
        snapshot(cpu=16, total=32768, available=24000), max_workers_cap=2
    )
    assert policy.max_workers <= 2
    assert policy.max_backtest_workers <= 2
    assert policy.max_simulation_workers <= 2
    assert policy.max_analysis_workers <= 2


def test_zero_memory_budget_defers_heavy_jobs():
    policy = derive_resource_policy(
        snapshot(cpu=8, total=8192, available=400), reserve_memory_mb=512
    )
    assert policy.memory_budget_mb == 0
    assert policy.defer_heavy_jobs
    assert policy.max_backtest_workers == 0


def test_manager_refreshes_policy_and_keeps_execution_permissions_separate(tmp_path):
    current = {"cpu": 2, "total": 3072, "available": 900}

    def sampler(*, root):
        return snapshot(
            cpu=current["cpu"],
            total=current["total"],
            available=current["available"],
        )

    manager = AdaptiveResourceManager(root=tmp_path, sampler=sampler)
    first = manager.refresh()
    current.update(cpu=8, total=16384, available=12000)
    second = manager.refresh()

    assert first.profile == "COMPACT"
    assert second.profile == "BALANCED"
    status = manager.status()
    assert status["permissions_changed"] is False
    assert status["trading_mode_changed"] is False
    assert status["policy"]["allow_real"] is False
    assert status["policy"]["auto_promote_real"] is False


def test_missing_memory_measurements_fail_conservatively():
    policy = derive_resource_policy(snapshot(total=0, available=0))
    assert policy.profile == "COMPACT"
    assert policy.defer_heavy_jobs
