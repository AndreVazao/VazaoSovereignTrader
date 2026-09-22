from __future__ import annotations

import json
from pathlib import Path

import pytest

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.core.engine import Position, SovereignEngine


class StagedExchange:
    name = "staged-exit-recovery"
    client = None

    def __init__(self, raw):
        self.raw = dict(raw)

    def fetch_order(self, order_id, symbol):
        return dict(self.raw)


def _config() -> dict:
    path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "partial-exit-restart-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}
    config["engine"]["paper_starting_balance"] = 1000
    return config


def _seed_position(engine: SovereignEngine) -> None:
    engine.state.open_positions["BTC/USDT"] = Position(
        exchange="staged-exit-recovery",
        symbol="BTC/USDT",
        entry=100.0,
        qty=1.0,
        stop=98.0,
        take_profit=104.0,
        opened_ts=1.0,
        entry_fee=0.10,
    )
    engine._persist_recovery()


def _pending_exit() -> dict:
    return {
        "exchange": "staged-exit-recovery",
        "symbol": "BTC/USDT",
        "side": "sell",
        "requested_qty": 1.0,
        "known_filled_qty": 0.0,
        "known_fill_price": 100.0,
        "known_quote_notional": 0.0,
        "known_fee": 0.0,
        "created_ts": 2.0,
        "client_order_id": "client-exit-partial-1",
        "stop_pct": 0.02,
        "take_profit_pct": 0.04,
        "reason": "partial exit recovery",
    }


def _exchange_for(raw):
    exchange = StagedExchange(raw)

    def resolve(_item):
        return exchange

    return resolve


def test_partial_exit_crash_restart_then_terminal_fill_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()

    first = SovereignEngine(config)
    _seed_position(first)
    first.state.pending_orders["exit-1"] = _pending_exit()
    first._persist_recovery()

    first_raw = {
        "id": "exit-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": 42.0,
        "fee": {"cost": 0.042, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(first, "_exchange_for_pending_order", _exchange_for(first_raw))
    first._reconcile_pending_orders()

    position = first.state.open_positions["BTC/USDT"]
    assert position.qty == 0.6
    assert position.entry == 100.0
    assert position.entry_fee == 0.06
    assert first.state.pending_orders["exit-1"]["known_filled_qty"] == 0.4
    assert first.state.pending_orders["exit-1"]["known_quote_notional"] == 42.0
    assert first.state.pending_orders["exit-1"]["known_fee"] == 0.042

    second = SovereignEngine(config)
    position = second.state.open_positions["BTC/USDT"]
    assert position.qty == 0.6
    assert position.entry_fee == 0.06
    assert second.state.pending_orders["exit-1"]["known_filled_qty"] == 0.4
    first_pnl_pct = ((2.0 - 0.04 - 0.042) / 40.0)
    assert second.risk.state.pnl_today_pct == pytest.approx(first_pnl_pct)
    assert second.risk.state.pnl_week_pct == pytest.approx(first_pnl_pct)

    second_raw = {
        "id": "exit-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "closed",
        "filled": 1.0,
        "average": 103.0,
        "cost": 103.0,
        "fee": {"cost": 0.102, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(second, "_exchange_for_pending_order", _exchange_for(second_raw))
    second._reconcile_pending_orders()

    assert second.state.open_positions == {}
    assert second.state.pending_orders == {}

    expected_pnl_pct = ((2.0 - 0.04 - 0.042) / 40.0) + ((1.0 - 0.06 - 0.06) / 60.0)
    assert second.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)
    assert second.risk.state.pnl_week_pct == pytest.approx(expected_pnl_pct)

    # Terminal removal is durable: another reconciliation cannot book the
    # terminal fill or P&L again.
    second._reconcile_pending_orders()
    assert second.state.open_positions == {}
    assert second.state.pending_orders == {}
    assert second.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)


def test_terminal_reconcile_crash_after_marker_persist_recovers_without_duplicate_fill(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()

    first = SovereignEngine(config)
    _seed_position(first)
    first.state.pending_orders["exit-crash-1"] = _pending_exit()
    first._persist_recovery()

    terminal_raw = {
        "id": "exit-crash-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "closed",
        "filled": 1.0,
        "average": 103.0,
        "cost": 103.0,
        "fee": {"cost": 0.102, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(first, "_exchange_for_pending_order", _exchange_for(terminal_raw))

    real_persist = first._persist_recovery
    persist_calls = {"count": 0}

    def crash_on_terminal_removal_persist():
        persist_calls["count"] += 1
        if persist_calls["count"] == 2:
            raise RuntimeError("simulated process crash before terminal pending-order removal")
        return real_persist()

    monkeypatch.setattr(first, "_persist_recovery", crash_on_terminal_removal_persist)
    first._reconcile_pending_orders()

    # The first durable snapshot contains the fully applied fill, but the
    # terminal pending order still exists because the process died before its
    # removal could be persisted.
    assert first.state.open_positions == {}
    assert first.state.pending_orders["exit-crash-1"]["known_filled_qty"] == pytest.approx(1.0)
    expected_pnl_pct = (103.0 - 100.0 - 0.10 - 0.102) / 100.0
    assert first.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)

    recovered = SovereignEngine(config)
    assert recovered.state.open_positions == {}
    assert recovered.state.pending_orders["exit-crash-1"]["known_filled_qty"] == pytest.approx(1.0)
    assert recovered.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)

    monkeypatch.setattr(recovered, "_exchange_for_pending_order", _exchange_for(terminal_raw))
    recovered._reconcile_pending_orders()

    assert recovered.state.open_positions == {}
    assert recovered.state.pending_orders == {}
    assert recovered.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)
    assert recovered.risk.state.pnl_week_pct == pytest.approx(expected_pnl_pct)

    # A further reconciliation cannot book the same terminal fill again.
    recovered._reconcile_pending_orders()
    assert recovered.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)
