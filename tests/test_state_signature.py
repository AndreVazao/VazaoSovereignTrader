from PC_ENGINE.learning.state_signature import StateSignature, StateSignatureLearningEngine

def _states(action="BUY"):
    return [{
        "symbol":"BTC/USDT", "timestamp_ms":1000+i*5000, "price":100+i*0.5,
        "regime":"UP_NORMAL", "trend":"UP", "volatility":"NORMAL", "action":action,
        "confluence_score":0.7, "confluence_confidence":0.8, "technical_score":0.6,
        "candlestick_bias":0.4, "radar_pressure":0.5, "lead_lag_score":0.3, "momentum_score":0.7,
        "mean_reversion_score":0.0, "order_flow_score":0.6, "breakout_score":0.4, "derivatives_score":0.2,
    } for i in range(80)]

def test_signature_is_deterministic_and_hierarchical():
    keys=StateSignature.hierarchy(_states()[0]); assert keys[0]==StateSignature.build(_states()[0]); assert len(keys)==4; assert keys[-1]=="UP_NORMAL"

def test_signature_learning_finds_positive_pattern():
    stats=StateSignatureLearningEngine(cost_bps=1,min_samples=5).evaluate(_states(), horizons_ms=(5000,)); exact=[r for r in stats if r.signature==StateSignature.build(_states()[0])]; assert exact and exact[0].eligible and exact[0].mean_net_bps>0

def test_signature_learning_reverses_sell_direction():
    stats=StateSignatureLearningEngine(cost_bps=1,min_samples=5).evaluate(_states("SELL"), horizons_ms=(5000,)); exact=[r for r in stats if r.signature==StateSignature.build(_states()[0])]; assert exact and exact[0].mean_net_bps<0

def test_rank_uses_fallback():
    states=_states(); engine=StateSignatureLearningEngine(cost_bps=1,min_samples=5); stats=engine.evaluate(states,horizons_ms=(5000,)); changed=dict(states[0]); changed["technical_score"]=-0.9; assert engine.rank(changed,stats,horizon_ms=5000) is not None
