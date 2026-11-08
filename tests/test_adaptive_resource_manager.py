from PC_ENGINE.core.adaptive_resource_manager import (
    AdaptiveResourceManager,
    ResourceSnapshot,
    derive_resource_policy,
    detect_system_resources,
)


def snapshot(cpu=2, total=3072, available=900, disk=100000, load=20):
    return ResourceSnapshot(
        cpu_count=cpu,
        memory_total_mb=total,
        memory_available_mb=available,
        disk_free_mb=disk,
        cpu_load_pct=load,
        os_name="Windows",
        sampled_at=1.0,
    )


def test_low_memory_machine_uses_compact_and_defers_heavy_jobs():
    policy = derive_resource_policy(snapshot())
    assert policy.profile == "COMPACT"
    assert policy.max_workers == 1
    assert policy.max_backtest_workers == 0
    assert policy.max_simulation_workers == 0
    assert policy.max_analysis_workers == 0
    assert policy.defer_heavy_jobs


def test_powerful_machine_scales_parallel_research():
    policy = derive_resource_policy(snapshot(cpu=16, total=32768, available=24000))
    assert policy.profile == "PERFORMANCE"
    assert policy.max_workers > 4
    assert policy.max_backtest_workers > 0
    assert policy.max_analysis_workers > 0
    assert not policy.defer_heavy_jobs


def test_high_load_temporarily_throttles_even_powerful_machine():
    policy = derive_resource_policy(snapshot(cpu=16, total=32768, available=20000, load=96))
    assert policy.profile == "COMPACT"
    assert policy.max_backtest_workers == 0
    assert policy.max_analysis_workers == 0
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
    assert policy.max_analysis_workers == 0


def test_manager_refreshes_budget_without_ignoring_total_memory_or_permissions(tmp_path):
    current = {"available": 900}

    def sampler(*, root):
        # Keep the physical RAM fixed at 3 GB; only available memory changes.
        return snapshot(total=3072, available=current["available"])

    manager = AdaptiveResourceManager(root=tmp_path, sampler=sampler)
    first = manager.refresh()
    current["available"] = 1500
    second = manager.refresh()

    assert first.profile == "COMPACT"
    # A 3 GB machine remains COMPACT even when more RAM becomes available.
    assert second.profile == "COMPACT"
    assert manager.snapshot is not None
    assert manager.snapshot.memory_available_mb == 1500
    assert second.memory_budget_mb == 988
    assert second.max_analysis_workers == 0
    status = manager.status()
    assert status["permissions_changed"] is False
    assert status["trading_mode_changed"] is False
    assert status["policy"]["allow_real"] is False
    assert status["policy"]["auto_promote_real"] is False


def test_detect_system_resources_reads_host_capacity():
    measured = detect_system_resources()
    assert measured.cpu_count >= 1
    assert measured.memory_total_mb > 0
    assert measured.memory_available_mb > 0
    assert measured.disk_free_mb > 0
    assert measured.os_name
    assert measured.cpu_load_pct is None or 0.0 <= measured.cpu_load_pct <= 100.0
