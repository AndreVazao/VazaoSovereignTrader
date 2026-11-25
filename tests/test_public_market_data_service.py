from __future__ import annotations

import json
from pathlib import Path

import pytest

from PC_ENGINE.services.public_market_data_service import PublicMarketDataService


class FakeProcess:
    _pid = 1000

    def __init__(self, command, **kwargs):
        FakeProcess._pid += 1
        self.pid = FakeProcess._pid
        self.command = command
        self.kwargs = kwargs
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        self.returncode = 0
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


def create_app(tmp_path: Path) -> Path:
    app = tmp_path / "app"
    app.mkdir()
    for name in (
        "VazaoSovereignTrader-Radar.exe",
        "VazaoSovereignTrader-TopOfBook.exe",
        "VazaoSovereignTrader-L2.exe",
        "VazaoSovereignTrader-MarketData.exe",
    ):
        (app / name).write_bytes(b"test executable")
    return app


def test_requires_all_fixed_workers_before_starting(tmp_path):
    app = create_app(tmp_path)
    (app / "VazaoSovereignTrader-L2.exe").unlink()
    with pytest.raises(FileNotFoundError, match="required_worker_missing"):
        PublicMarketDataService(app, tmp_path / "data")


def test_builds_only_fixed_public_data_worker_commands(tmp_path):
    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data", symbols=["BTC/USDT", "ETH/USDT", "BTC/USDT"])
    assert [worker.name for worker in service.workers] == [
        "radar_rest", "top_of_book", "order_book_l2", "market_data_learning"
    ]
    assert all(worker.command[0].startswith(str(app)) for worker in service.workers)
    assert all("--data-dir" in worker.command for worker in service.workers)
    assert all("--stop-file" in worker.command for worker in service.workers)
    assert service.symbols == ["BTC/USDT", "ETH/USDT"]
    assert all("private" not in " ".join(worker.command).lower() for worker in service.workers)


def test_start_and_stop_own_exact_child_processes(tmp_path):
    app = create_app(tmp_path)
    processes = []

    def popen(command, **kwargs):
        process = FakeProcess(command, **kwargs)
        processes.append(process)
        return process

    service = PublicMarketDataService(app, tmp_path / "data", popen=popen)
    service.start()
    assert len(processes) == 4
    assert all(process.kwargs["shell"] is False for process in processes)
    assert all(process.kwargs["stdin"] is not None for process in processes)
    assert service.snapshot()["all_workers_running"] is True

    service.stop()
    assert all(process.returncode == 0 for process in processes)
    assert all(process.terminated is False for process in processes)
    assert all(worker.process is None for worker in service.workers)


def test_health_age_uses_collector_timestamp_and_rejects_invalid_json(tmp_path):
    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data")
    worker = service.workers[0]
    worker.health_file.parent.mkdir(parents=True, exist_ok=True)
    worker.health_file.write_text(json.dumps({"timestamp_ms": 1}), encoding="utf-8")
    assert service._health_age(worker) is not None
    worker.health_file.write_text("{broken", encoding="utf-8")
    assert service._health_age(worker) is None


def test_worker_restart_rate_is_bounded(tmp_path):
    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data", restart_limit=1, popen=FakeProcess)
    worker = service.workers[0]
    assert service._start_worker(worker) is True
    service._stop_worker(worker)
    assert service._start_worker(worker) is False
    assert worker.last_error == "restart_rate_limit_exceeded"


def test_health_report_is_atomic_and_marks_paper_only(tmp_path):
    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data", popen=FakeProcess)
    service.start()
    service._write_health("RUNNING")
    report = json.loads((tmp_path / "data" / "market_data_service_health.json").read_text())
    assert report["paper_only"] is True
    assert report["private_account_access"] is False
    assert report["orders_submitted"] is False
    assert "all_worker_heartbeats_fresh" in report
    assert report["execution_authorized"] is False
    service.stop()


def test_singleton_lock_prevents_duplicate_supervisor_instances(tmp_path):
    app = create_app(tmp_path)
    first = PublicMarketDataService(app, tmp_path / "data", popen=FakeProcess)
    second = PublicMarketDataService(app, tmp_path / "data", popen=FakeProcess)
    first.start()
    try:
        with pytest.raises(RuntimeError, match="already_running"):
            second.start()
    finally:
        first.stop()


def test_cooperative_stop_file_sets_event_and_runs_callback(tmp_path):
    import threading
    import time
    from PC_ENGINE.services.stop_file import watch_stop_file

    event = threading.Event()
    called = []
    request = tmp_path / "stop.request"
    watcher = watch_stop_file(event, request, on_stop=lambda: called.append(True), poll_seconds=0.05)
    request.write_text("stop", encoding="ascii")
    assert event.wait(1.0)
    watcher.join(timeout=1.0)
    assert called == [True]
    assert request.exists() is False


def test_failed_worker_launch_consumes_restart_budget_and_can_retry(tmp_path):
    app = create_app(tmp_path)
    attempts = []

    def popen(command, **kwargs):
        attempts.append(command)
        if len(attempts) == 1:
            raise OSError("temporary launch failure")
        return FakeProcess(command, **kwargs)

    service = PublicMarketDataService(app, tmp_path / "data", restart_limit=2, popen=popen)
    worker = service.workers[0]
    assert service._start_worker(worker) is False
    assert len(worker.restarts) == 1
    assert worker.last_start_ms > 0
    assert service._start_worker(worker) is True
    assert len(worker.restarts) == 2


def test_new_supervisor_start_clears_stale_stop_request(tmp_path):
    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data", popen=FakeProcess)
    service.data_dir.mkdir(parents=True, exist_ok=True)
    service.control_file.write_text("stop", encoding="ascii")
    service.start()
    try:
        assert service.control_file.exists() is False
    finally:
        service.stop()


def test_storage_budget_counts_persistent_files_without_following_symlinks(tmp_path):
    app = create_app(tmp_path)
    data = tmp_path / "data"
    service = PublicMarketDataService(app, data, max_data_dir_bytes=1024 * 1024)
    (data / "radar").mkdir(parents=True)
    (data / "radar" / "events.jsonl").write_bytes(b"x" * 4096)
    assert service._storage_usage_bytes() >= 4096
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"y" * 8192)
    link = data / "radar" / "external.bin"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return
    assert service._storage_usage_bytes() == 4096


def test_supervisor_refuses_to_start_when_storage_budget_is_exhausted(tmp_path):
    app = create_app(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "existing.jsonl").write_bytes(b"x" * (1024 * 1024))
    started = []
    service = PublicMarketDataService(
        app, data, max_data_dir_bytes=1024 * 1024,
        popen=lambda *args, **kwargs: started.append(args),
    )
    service.start()
    try:
        assert started == []
        assert service.shutdown_reason == "storage_limit_reached_before_start"
        report = json.loads((data / "market_data_service_health.json").read_text())
        assert report["storage"]["budget_exhausted"] is True
        assert report["shutdown_reason"] == "storage_limit_reached_before_start"
    finally:
        service.stop()


def test_default_storage_budget_is_five_gib(tmp_path):
    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data")
    assert service.max_data_dir_bytes == 5 * 1024 * 1024 * 1024


def test_retention_deletes_only_expired_jsonl_and_preserves_reports(tmp_path):
    import os
    import time

    app = create_app(tmp_path)
    data = tmp_path / "data"
    radar = data / "radar"
    radar.mkdir(parents=True)
    expired = radar / "old_events.jsonl"
    recent = radar / "recent_events.jsonl"
    report = radar / "venue_economic_evidence.json"
    expired.write_text('{"old":true}\\n', encoding="utf-8")
    recent.write_text('{"new":true}\\n', encoding="utf-8")
    report.write_text('{"generated_at_ms":1}\\n', encoding="utf-8")
    old = time.time() - (31 * 24 * 60 * 60)
    os.utime(expired, (old, old))
    os.utime(report, (old, old))
    service = PublicMarketDataService(app, data)
    service._prune_expired_market_data()
    assert not expired.exists()
    assert recent.exists()
    assert report.exists()
    assert service.retention_snapshot["expired_files_deleted"] == 1


def test_retention_deletes_expired_rotated_jsonl_backup(tmp_path):
    import os
    import time

    app = create_app(tmp_path)
    data = tmp_path / "data"
    radar = data / "radar"
    radar.mkdir(parents=True)
    backup = radar / "l2_events.jsonl.1"
    backup.write_bytes(b'{"old":true}\n')
    old = time.time() - (31 * 24 * 60 * 60)
    os.utime(backup, (old, old))

    service = PublicMarketDataService(app, data)
    service._prune_expired_market_data()

    assert not backup.exists()
    assert service.retention_snapshot["expired_files_deleted"] == 1


def test_retention_runs_periodically_while_service_is_active(tmp_path):
    import os
    import time

    app = create_app(tmp_path)
    data = tmp_path / "data"
    clock_value = [1000.0]
    service = PublicMarketDataService(
        app,
        data,
        clock=lambda: clock_value[0],
        retention_check_interval_seconds=60,
    )

    assert service._run_retention_if_due(force=True) is True
    assert service._run_retention_if_due() is False

    expired = data / "radar" / "arrived_after_start.jsonl"
    expired.parent.mkdir(parents=True, exist_ok=True)
    expired.write_text('{"old":true}\n', encoding="utf-8")
    old = time.time() - (31 * 24 * 60 * 60)
    os.utime(expired, (old, old))

    clock_value[0] += 61
    assert service._run_retention_if_due() is True
    assert not expired.exists()
    assert service.retention_snapshot["last_run_ts_ms"] is not None



def test_stop_requests_all_workers_before_waiting_for_any_child(tmp_path):
    app = create_app(tmp_path)
    processes = []
    service_holder = {}

    class VerifyingProcess(FakeProcess):
        def wait(self, timeout=None):
            service = service_holder["service"]
            assert all(worker.stop_file.exists() for worker in service.workers)
            return super().wait(timeout)

    def popen(command, **kwargs):
        process = VerifyingProcess(command, **kwargs)
        processes.append(process)
        return process

    service = PublicMarketDataService(app, tmp_path / "data", popen=popen)
    service_holder["service"] = service
    service.start()
    service.stop()

    assert len(processes) == 4
    assert all(process.returncode == 0 for process in processes)
    assert all(worker.process is None for worker in service.workers)
    health = json.loads((service.data_dir / "market_data_service_health.json").read_text())
    assert health["status"] == "STOPPED"


def test_supervisor_never_reports_stopped_or_releases_lock_with_live_child(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data", popen=FakeProcess)
    service.start()
    live_processes = [worker.process for worker in service.workers]
    original_stop_worker = service._stop_worker

    def leave_child_running(worker):
        worker.last_error = "worker_stop_timeout"

    monkeypatch.setattr(service, "_stop_worker", leave_child_running)
    service.stop()

    assert all(worker.process is not None for worker in service.workers)
    assert all(process.poll() is None for process in live_processes)
    assert service._instance_lock_handle is not None
    assert service.shutdown_reason == "worker_shutdown_timeout"
    health = json.loads((service.data_dir / "market_data_service_health.json").read_text())
    assert health["status"] == "DEGRADED"
    assert health["shutdown_reason"] == "worker_shutdown_timeout"

    # Simulate the children exiting after the timeout, then permit a clean retry.
    for process in live_processes:
        process.returncode = 0
    monkeypatch.setattr(service, "_stop_worker", original_stop_worker)
    service.stop()
    assert service._instance_lock_handle is None
    assert all(worker.process is None for worker in service.workers)
    health = json.loads((service.data_dir / "market_data_service_health.json").read_text())
    assert health["status"] == "STOPPED"



def test_explicit_degraded_shutdown_status_overrides_fresh_worker_heartbeats(tmp_path):
    import time

    app = create_app(tmp_path)
    service = PublicMarketDataService(app, tmp_path / "data", popen=FakeProcess)
    service.start()
    now_ms = time.time_ns() // 1_000_000
    for worker in service.workers:
        worker.health_file.parent.mkdir(parents=True, exist_ok=True)
        worker.health_file.write_text(json.dumps({"timestamp_ms": now_ms}), encoding="utf-8")

    assert service.snapshot()["all_workers_running"] is True
    assert service.snapshot()["all_worker_heartbeats_fresh"] is True
    service.shutdown_reason = "worker_shutdown_timeout"
    service._write_health("DEGRADED")

    health = json.loads((service.data_dir / "market_data_service_health.json").read_text())
    assert health["status"] == "DEGRADED"
    assert health["shutdown_reason"] == "worker_shutdown_timeout"
    service.stop()
