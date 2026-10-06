from __future__ import annotations

import multiprocessing
from pathlib import Path

from PC_ENGINE.storage.ledger import Ledger


def _write_idempotent(path: str, key: str, queue) -> None:
    ledger = Ledger(path=Path(path))
    queue.put(ledger.trade_idempotent({"symbol": "BTC/USDT"}, key))


def test_trade_idempotent_serializes_concurrent_processes(tmp_path):
    path = tmp_path / "trades.jsonl"
    key = "reconcile-concurrent-1"
    queue = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(
            target=_write_idempotent,
            args=(str(path), key, queue),
        )
        for _ in range(2)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=10)

    try:
        results = [queue.get(timeout=5), queue.get(timeout=5)]
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()

    assert all(process.exitcode == 0 for process in processes)
    assert sorted(results) == [False, True]

    rows = Ledger(path=path).read_trades()
    assert len(rows) == 1
    assert rows[0]["reconciliation_key"] == key


def test_trade_idempotent_uses_persistent_lock_file(tmp_path):
    path = tmp_path / "trades.jsonl"
    ledger = Ledger(path=path)

    assert ledger.trade_idempotent({"symbol": "ETH/USDT"}, "key-1") is True
    assert ledger.trade_idempotent({"symbol": "ETH/USDT"}, "key-1") is False
    assert path.with_name("trades.jsonl.lock").exists()


def test_trade_idempotent_requires_key(tmp_path):
    ledger = Ledger(path=tmp_path / "trades.jsonl")

    try:
        ledger.trade_idempotent({"symbol": "BTC/USDT"}, "")
    except ValueError as exc:
        assert str(exc) == "idempotency_key is required"
    else:
        raise AssertionError("missing idempotency key must fail")
