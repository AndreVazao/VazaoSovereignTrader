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


@pytest.mark.parametrize(
    ("raw", "expected_safe"),
    [
        ({"filled": 0.0, "average": 105.0, "cost": 1.0}, True),
        ({"filled": 0.0, "average": 105.0, "cost": 0.0, "fee": {"cost": 0.01, "currency": "USDT"}}, True),
        ({"filled": 0.0, "average": 0.0, "cost": 0.0, "fee": {"cost": 0.0, "currency": "USDT"}}, True),
    ],
)
def test_pending_reconciliation_zero_fill_financial_values_fail_closed(
    tmp_path, monkeypatch, raw, expected_safe
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    engine.state.pending_orders["zero-fill-financial-1"] = _pending_exit()
    engine._persist_recovery()

    response = {
        "id": "zero-fill-financial-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": 42.0,
        "fee": {"cost": 0.042, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    response.update(raw)
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(response))

    engine._reconcile_pending_orders()

    assert (engine.state.status == "SAFE_MODE") is expected_safe
    if expected_safe:
        assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
        item = engine.state.pending_orders["zero-fill-financial-1"]
        assert item["known_filled_qty"] == pytest.approx(0.0)
        assert item["known_quote_notional"] == pytest.approx(0.0)
        assert item["known_fee"] == pytest.approx(0.0)
        assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


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

    def crash_after_marker_persist():
        persist_calls["count"] += 1
        real_persist()
        if persist_calls["count"] == 1:
            raise RuntimeError("simulated process crash after durable fill marker")

    monkeypatch.setattr(first, "_persist_recovery", crash_after_marker_persist)
    first._reconcile_pending_orders()

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

    recovered._reconcile_pending_orders()
    assert recovered.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)


@pytest.mark.parametrize(
    ("field", "value", "expected_log"),
    [
        ("symbol", "ETH/USDT", "PENDING_ORDER_SYMBOL_MISMATCH"),
        ("side", "buy", "PENDING_ORDER_SIDE_MISMATCH"),
        ("clientOrderId", "wrong-client-id", "PENDING_ORDER_IDENTITY_MISMATCH"),
    ],
)
def test_pending_reconciliation_identity_mismatch_fails_closed(tmp_path, monkeypatch, field, value, expected_log):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    engine.state.pending_orders["identity-1"] = _pending_exit()
    engine._persist_recovery()

    raw = {
        "id": "identity-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "closed",
        "filled": 1.0,
        "average": 103.0,
        "cost": 103.0,
        "fee": {"cost": 0.102, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    raw[field] = value
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(raw))

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    assert engine.state.pending_orders["identity-1"]["known_filled_qty"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("raw_filled", "raw_cost", "raw_fee", "expected_log"),
    [
        (0.2, 20.0, 0.02, "PENDING_ORDER_FILL_REGRESSION"),
    ],
)
def test_pending_reconciliation_cumulative_fill_regression_fails_closed(
    tmp_path, monkeypatch, raw_filled, raw_cost, raw_fee, expected_log
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    pending = _pending_exit()
    pending["known_filled_qty"] = 0.4
    pending["known_quote_notional"] = 42.0
    pending["known_fee"] = 0.042
    engine.state.pending_orders["regression-1"] = pending
    engine._persist_recovery()

    raw = {
        "id": "regression-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": raw_filled,
        "average": 100.0,
        "cost": raw_cost,
        "fee": {"cost": raw_fee, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(raw))

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    assert engine.state.pending_orders["regression-1"]["known_filled_qty"] == pytest.approx(0.4)
    assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("known_fee", "raw_fee"),
    [(0.042, 0.02)],
)
def test_pending_reconciliation_cumulative_fee_regression_fails_closed(
    tmp_path, monkeypatch, known_fee, raw_fee
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    pending = _pending_exit()
    pending["known_filled_qty"] = 0.4
    pending["known_quote_notional"] = 42.0
    pending["known_fee"] = known_fee
    engine.state.pending_orders["fee-regression-1"] = pending
    engine._persist_recovery()

    raw = {
        "id": "fee-regression-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": 42.0,
        "fee": {"cost": raw_fee, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(raw))

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    item = engine.state.pending_orders["fee-regression-1"]
    assert item["known_filled_qty"] == pytest.approx(0.4)
    assert item["known_quote_notional"] == pytest.approx(42.0)
    assert item["known_fee"] == pytest.approx(known_fee)
    assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("known_notional", "raw_cost"),
    [(42.0, 40.0)],
)
def test_pending_reconciliation_cumulative_notional_regression_fails_closed(
    tmp_path, monkeypatch, known_notional, raw_cost
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    pending = _pending_exit()
    pending["known_filled_qty"] = 0.4
    pending["known_quote_notional"] = known_notional
    pending["known_fee"] = 0.042
    engine.state.pending_orders["notional-regression-1"] = pending
    engine._persist_recovery()

    raw = {
        "id": "notional-regression-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": raw_cost,
        "fee": {"cost": 0.042, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(raw))

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    item = engine.state.pending_orders["notional-regression-1"]
    assert item["known_filled_qty"] == pytest.approx(0.4)
    assert item["known_quote_notional"] == pytest.approx(known_notional)
    assert item["known_fee"] == pytest.approx(0.042)
    assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("raw_cost", "raw_fee"),
    [(42.0, -0.001), (-42.0, 0.042)],
)
def test_pending_reconciliation_negative_financial_value_fails_closed(
    tmp_path, monkeypatch, raw_cost, raw_fee
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    engine.state.pending_orders["negative-financial-1"] = _pending_exit()
    engine._persist_recovery()

    raw = {
        "id": "negative-financial-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": raw_cost,
        "fee": {"cost": raw_fee, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(raw))

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    item = engine.state.pending_orders["negative-financial-1"]
    assert item["known_filled_qty"] == pytest.approx(0.0)
    assert item["known_quote_notional"] == pytest.approx(0.0)
    assert item["known_fee"] == pytest.approx(0.0)
    assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("field", "raw_value"),
    [
        ("average", float("nan")),
        ("average", float("inf")),
        ("cost", float("nan")),
        ("cost", float("inf")),
        ("fee", {"cost": float("nan"), "currency": "USDT"}),
        ("fee", {"cost": float("inf"), "currency": "USDT"}),
    ],
)
def test_pending_reconciliation_nonfinite_financial_value_fails_closed(
    tmp_path, monkeypatch, field, raw_value
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    engine.state.pending_orders["nonfinite-financial-1"] = _pending_exit()
    engine._persist_recovery()

    raw = {
        "id": "nonfinite-financial-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": 42.0,
        "fee": {"cost": 0.042, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    raw[field] = raw_value
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(raw))

    engine._reconcile_pending_orders()

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    item = engine.state.pending_orders["nonfinite-financial-1"]
    assert item["known_filled_qty"] == pytest.approx(0.0)
    assert item["known_quote_notional"] == pytest.approx(0.0)
    assert item["known_fee"] == pytest.approx(0.0)
    assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("raw", "expected_safe"),
    [
        ({"filled": 0.0, "average": 105.0, "cost": 1.0}, True),
        ({"filled": 0.4, "average": 105.0, "cost": 42.0, "fee": {"cost": 50.0, "currency": "USDT"}}, True),
        ({"filled": 0.4, "average": 105.0, "cost": 1.0}, True),
    ],
)
def test_pending_reconciliation_impossible_financial_relationships_fail_closed(
    tmp_path, monkeypatch, raw, expected_safe
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    engine.state.pending_orders["impossible-financial-1"] = _pending_exit()
    engine._persist_recovery()

    response = {
        "id": "impossible-financial-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": 42.0,
        "fee": {"cost": 0.042, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    response.update(raw)
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(response))

    engine._reconcile_pending_orders()

    assert (engine.state.status == "SAFE_MODE") is expected_safe
    if expected_safe:
        assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
        item = engine.state.pending_orders["impossible-financial-1"]
        assert item["known_filled_qty"] == pytest.approx(0.0)
        assert item["known_quote_notional"] == pytest.approx(0.0)
        assert item["known_fee"] == pytest.approx(0.0)
        assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


def test_crash_after_financial_application_before_marker_persist_is_recoverable_without_duplicate_fill(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()

    first = SovereignEngine(config)
    _seed_position(first)
    first.state.pending_orders["exit-financial-crash-1"] = _pending_exit()
    first._persist_recovery()

    terminal_raw = {
        "id": "exit-financial-crash-1",
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

    def crash_before_marker_persist():
        persist_calls["count"] += 1
        if persist_calls["count"] == 1:
            raise RuntimeError("simulated persistence failure before applied-fill marker")
        real_persist()

    monkeypatch.setattr(first, "_persist_recovery", crash_before_marker_persist)
    first._reconcile_pending_orders()

    assert first.state.open_positions == {}
    assert first.state.pending_orders["exit-financial-crash-1"]["known_filled_qty"] == pytest.approx(1.0)
    expected_pnl_pct = (103.0 - 100.0 - 0.10 - 0.102) / 100.0
    assert first.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)

    recovered = SovereignEngine(config)
    assert recovered.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    assert recovered.state.pending_orders["exit-financial-crash-1"]["known_filled_qty"] == pytest.approx(0.0)
    assert recovered.risk.state.pnl_today_pct == pytest.approx(0.0)

    monkeypatch.setattr(recovered, "_exchange_for_pending_order", _exchange_for(terminal_raw))
    recovered._reconcile_pending_orders()

    assert recovered.state.open_positions == {}
    assert recovered.state.pending_orders == {}
    assert recovered.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)
    recovered._reconcile_pending_orders()
    assert recovered.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)


@pytest.mark.parametrize(
    ("raw", "expected_safe"),
    [
        (
            {
                "id": "cumulative-notional-inconsistent-1",
                "symbol": "BTC/USDT",
                "side": "sell",
                "status": "open",
                "filled": 0.8,
                "average": 100.0,
                "cost": 50.0,
                "fee": {"cost": 0.05, "currency": "USDT"},
                "clientOrderId": "client-exit-partial-1",
            },
            True,
        ),
        (
            {
                "id": "cumulative-notional-inconsistent-2",
                "symbol": "BTC/USDT",
                "side": "sell",
                "status": "open",
                "filled": 0.0,
                "average": 100.0,
                "cost": 1.0,
                "fee": {"cost": 0.001, "currency": "USDT"},
                "clientOrderId": "client-exit-partial-1",
            },
            True,
        ),
    ],
)
def test_pending_reconciliation_cumulative_notional_invariants_fail_closed(
    tmp_path, monkeypatch, raw, expected_safe
):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    engine = SovereignEngine(config)
    _seed_position(engine)
    engine.state.pending_orders["cumulative-notional-1"] = _pending_exit()
    engine._persist_recovery()
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(raw))

    engine._reconcile_pending_orders()

    assert (engine.state.status == "SAFE_MODE") is expected_safe
    item = engine.state.pending_orders["cumulative-notional-1"]
    assert item["known_filled_qty"] == pytest.approx(0.0)
    assert item["known_quote_notional"] == pytest.approx(0.0)
    assert item["known_fee"] == pytest.approx(0.0)
    assert engine.state.open_positions["BTC/USDT"].qty == pytest.approx(1.0)
    assert engine.risk.state.pnl_today_pct == pytest.approx(0.0)


def test_multi_fill_reconciliation_with_changing_average_price_applies_only_incremental_financials(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()

    engine = SovereignEngine(config)
    _seed_position(engine)
    engine.state.pending_orders["multi-fill-1"] = _pending_exit()
    engine._persist_recovery()

    first_raw = {
        "id": "multi-fill-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.4,
        "average": 105.0,
        "cost": 42.0,
        "fee": {"cost": 0.042, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(first_raw))
    engine._reconcile_pending_orders()

    position = engine.state.open_positions["BTC/USDT"]
    assert position.qty == pytest.approx(0.6)
    assert position.entry_fee == pytest.approx(0.06)
    assert engine.state.pending_orders["multi-fill-1"]["known_filled_qty"] == pytest.approx(0.4)
    assert engine.state.pending_orders["multi-fill-1"]["known_quote_notional"] == pytest.approx(42.0)
    assert engine.state.pending_orders["multi-fill-1"]["known_fee"] == pytest.approx(0.042)

    second_raw = {
        "id": "multi-fill-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "open",
        "filled": 0.7,
        "average": 107.14285714285714,
        "cost": 75.0,
        "fee": {"cost": 0.075, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(second_raw))
    engine._reconcile_pending_orders()

    position = engine.state.open_positions["BTC/USDT"]
    assert position.qty == pytest.approx(0.3)
    assert position.entry_fee == pytest.approx(0.03)
    item = engine.state.pending_orders["multi-fill-1"]
    assert item["known_filled_qty"] == pytest.approx(0.7)
    assert item["known_quote_notional"] == pytest.approx(75.0)
    assert item["known_fee"] == pytest.approx(0.075)

    expected_pnl_pct = ((2.0 - 0.04 - 0.042) / 40.0) + ((33.0 - 0.03 - 0.033) / 30.0)
    assert engine.risk.state.pnl_today_pct == pytest.approx(expected_pnl_pct)

    third_raw = {
        "id": "multi-fill-1",
        "symbol": "BTC/USDT",
        "side": "sell",
        "status": "closed",
        "filled": 1.0,
        "average": 108.0,
        "cost": 108.0,
        "fee": {"cost": 0.108, "currency": "USDT"},
        "clientOrderId": "client-exit-partial-1",
    }
    monkeypatch.setattr(engine, "_exchange_for_pending_order", _exchange_for(third_raw))
    engine._reconcile_pending_orders()

    assert engine.state.open_positions == {}
    assert engine.state.pending_orders == {}
    final_expected = expected_pnl_pct + ((33.0 - 0.03 - 0.033) / 30.0)
    assert engine.risk.state.pnl_today_pct == pytest.approx(final_expected)
    engine._reconcile_pending_orders()
    assert engine.risk.state.pnl_today_pct == pytest.approx(final_expected)
