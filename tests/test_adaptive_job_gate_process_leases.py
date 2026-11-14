from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobGate
from PC_ENGINE.core.adaptive_resource_manager import ResourcePolicy


class _Manager:
    def __init__(self, backtest_limit: int):
        self.backtest_limit = backtest_limit

    def refresh(self):
        return ResourcePolicy(
            "BALANCED",
            2,
            self.backtest_limit,
            1,
            1,
            1024,
            False,
            (),
        )


def _lease_child(root, connection, release_event, backtest_limit=1, crash=False):
    gate = AdaptiveJobGate(
        _Manager(backtest_limit),
        lease_root=Path(root),
    )
    with gate.slot("backtest") as admitted:
        connection.send(admitted)
        connection.close()
        if admitted and crash:
            os._exit(0)
        if admitted:
            release_event.wait(15)


def _start_child(ctx, root, release_event, *, backtest_limit=1, crash=False):
    receive_connection, send_connection = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_lease_child,
        args=(
            str(root),
            send_connection,
            release_event,
            backtest_limit,
            crash,
        ),
    )
    process.start()
    send_connection.close()
    assert receive_connection.poll(10), "worker did not report its lease result"
    admitted = receive_connection.recv()
    receive_connection.close()
    return process, admitted


def test_process_wide_lease_blocks_a_second_process_until_release(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    release_event = ctx.Event()

    first, first_admitted = _start_child(ctx, tmp_path, release_event)
    assert first_admitted is True

    second, second_admitted = _start_child(ctx, tmp_path, release_event)
    assert second_admitted is False
    second.join(10)
    assert second.exitcode == 0

    release_event.set()
    first.join(10)
    assert first.exitcode == 0

    third, third_admitted = _start_child(ctx, tmp_path, release_event)
    assert third_admitted is True
    third.join(10)
    assert third.exitcode == 0


def test_process_exit_releases_lease_without_python_cleanup(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    release_event = ctx.Event()

    crashed, admitted = _start_child(
        ctx,
        tmp_path,
        release_event,
        crash=True,
    )
    assert admitted is True
    crashed.join(10)
    assert crashed.exitcode == 0

    next_process, next_admitted = _start_child(
        ctx,
        tmp_path,
        release_event,
    )
    assert next_admitted is True
    release_event.set()
    next_process.join(10)
    assert next_process.exitcode == 0


def test_current_lower_budget_counts_existing_process_leases(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    release_event = ctx.Event()

    first, first_admitted = _start_child(
        ctx,
        tmp_path,
        release_event,
        backtest_limit=2,
    )
    second, second_admitted = _start_child(
        ctx,
        tmp_path,
        release_event,
        backtest_limit=2,
    )
    assert first_admitted is True
    assert second_admitted is True

    lower_budget, lower_admitted = _start_child(
        ctx,
        tmp_path,
        release_event,
        backtest_limit=1,
    )
    assert lower_admitted is False
    lower_budget.join(10)
    assert lower_budget.exitcode == 0

    release_event.set()
    first.join(10)
    second.join(10)
    assert first.exitcode == 0
    assert second.exitcode == 0


def test_gate_instances_in_one_process_share_the_lease_budget(tmp_path):
    first_gate = AdaptiveJobGate(_Manager(1), lease_root=tmp_path)
    second_gate = AdaptiveJobGate(_Manager(1), lease_root=tmp_path)

    with first_gate.slot("backtest") as first:
        assert first is True
        with second_gate.slot("backtest") as second:
            assert second is False

    assert first_gate.snapshot()["active"]["backtest"] == 0
    assert first_gate.snapshot()["process_wide_leases"] is True


def test_unavailable_lease_directory_fails_closed(tmp_path):
    blocked_root = tmp_path / "not-a-directory"
    blocked_root.write_text("occupied", encoding="utf-8")
    gate = AdaptiveJobGate(
        _Manager(1),
        lease_root=blocked_root / "leases",
    )

    with gate.slot("backtest") as admitted:
        assert admitted is False

    assert gate.snapshot()["active"]["backtest"] == 0
