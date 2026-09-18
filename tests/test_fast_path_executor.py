from types import SimpleNamespace

from PC_ENGINE.core.fast_path import FastPathDecision
from PC_ENGINE.core.fast_path_executor import FastPathExecutor


def decision():
    return FastPathDecision(
        accepted=True,
        reason="validated_fast_path",
        symbol="BTC/USDT",
        direction="UP",
        leader="binance",
        follower="okx",
        horizon_ms=1000,
        expectancy_bps=8.0,
        confidence=0.9,
        age_ms=10,
        evaluation_ns=100,
    )


def test_disabled_never_calls_order():
    calls = []
    result = FastPathExecutor(enabled=False).execute(
        decision(), {"price": 100}, mode="PAPER",
        authorize=lambda *_: (True, "ok"),
        order=lambda *_: calls.append(1),
    )
    assert result.reason == "fast_path_disabled"
    assert calls == []


def test_real_is_blocked_by_default():
    result = FastPathExecutor(enabled=True, allow_real=False).execute(
        decision(), {"price": 100}, mode="REAL",
        authorize=lambda *_: (True, "ok"),
        order=lambda *_: SimpleNamespace(ok=True, reason="filled", order_id="1", qty=1, price=100),
    )
    assert not result.accepted
    assert result.reason == "real_fast_path_disabled"


def test_risk_authorization_happens_before_order():
    calls = []
    result = FastPathExecutor(enabled=True).execute(
        decision(), {"price": 100}, mode="PAPER",
        authorize=lambda *_: (False, "risk_rejected"),
        order=lambda *_: calls.append(1),
    )
    assert not result.accepted
    assert result.reason == "risk_rejected"
    assert calls == []


def test_paper_order_is_executed_after_authorization():
    result = FastPathExecutor(enabled=True).execute(
        decision(), {"price": 100}, mode="PAPER",
        authorize=lambda *_: (True, "ok"),
        order=lambda *_: SimpleNamespace(ok=True, reason="paper fill", order_id="paper-buy", qty=0.01, price=100.1),
    )
    assert result.accepted
    assert result.attempted
    assert result.order_id == "paper-buy"
    assert result.qty == 0.01
