import json

from PC_ENGINE.core.risk import RiskEngine


def _risk(tmp_path, observed_at_ms=None):
    path = tmp_path / "state_outcomes.jsonl"
    row = {
        "symbol": "BTC/USDT", "action": "BUY", "regime": "TREND", "horizon_ms": 5000,
        "samples": 400, "wins": 320, "mean_net_bps": 6, "lower_ci_bps": 2, "eligible": True,
    }
    if observed_at_ms is not None:
        row["observed_at_ms"] = observed_at_ms
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return RiskEngine({
        "max_daily_loss_pct": -0.02, "max_weekly_loss_pct": -0.06,
        "kill_cooldown_seconds": 60, "max_symbol_loss_streak": 3,
        "cooldown_after_loss_seconds": 60, "risk_per_trade_pct": 0.005,
        "adaptive_risk": {"min_samples": 100, "base_multiplier": 1.0, "max_multiplier": 1.5, "outcome_path": str(path)},
    })


def test_automatic_evidence_scales_contextual_risk(tmp_path):
    risk = _risk(tmp_path, observed_at_ms=9999999999999)
    sized, snap = risk.adaptive_position_notional_auto(
        10_000, 0.01, strategy_id="trend_ema_atr", symbol="BTC/USDT",
        regime="TREND", horizon_seconds=5,
    )
    assert snap.eligible
    assert snap.samples == 400
    assert sized > risk.position_notional(10_000, 0.01)


def test_missing_automatic_evidence_fails_closed(tmp_path):
    risk = _risk(tmp_path, observed_at_ms=9999999999999)
    sized, snap = risk.adaptive_position_notional_auto(
        10_000, 0.01, strategy_id="trend_ema_atr", symbol="ETH/USDT",
        regime="TREND", horizon_seconds=5,
    )
    assert not snap.eligible
    assert snap.multiplier == 0.5
    assert sized < risk.position_notional(10_000, 0.01)


def test_stale_automatic_evidence_fails_closed(tmp_path):
    import time
    risk = _risk(tmp_path, observed_at_ms=int(time.time() * 1000) - 86_400_001)
    sized, snap = risk.adaptive_position_notional_auto(
        10_000, 0.01, strategy_id="trend_ema_atr", symbol="BTC/USDT",
        regime="TREND", horizon_seconds=5,
    )
    assert not snap.eligible
    assert snap.multiplier == 0.5
    assert sized < risk.position_notional(10_000, 0.01)
