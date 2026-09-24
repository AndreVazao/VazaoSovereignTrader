from PC_ENGINE.core.cost_model import OpportunityCostGate


def test_cost_gate_accepts_edge_only_after_all_costs():
    gate = OpportunityCostGate(minimum_net_edge_bps=5.0, minimum_edge_margin_bps=2.0)
    result = gate.evaluate(
        gross_edge_bps=40.0,
        fee_bps=8.0,
        spread_bps=5.0,
        slippage_bps=6.0,
        liquidity_bps=4.0,
        latency_bps=3.0,
    )
    assert result.total_bps == 26.0
    assert result.net_edge_bps == 14.0
    assert result.viable is True


def test_cost_gate_blocks_negative_or_insufficient_net_edge():
    gate = OpportunityCostGate(minimum_net_edge_bps=5.0, minimum_edge_margin_bps=2.0)
    result = gate.evaluate(
        gross_edge_bps=20.0,
        fee_bps=8.0,
        spread_bps=5.0,
        slippage_bps=6.0,
        liquidity_bps=4.0,
        latency_bps=3.0,
    )
    assert result.viable is False
    assert result.net_edge_bps == -6.0
    assert result.reason == "net edge below minimum"


def test_cost_gate_rejects_non_finite_costs():
    gate = OpportunityCostGate()
    try:
        gate.evaluate(gross_edge_bps=20.0, slippage_bps=float("nan"))
    except ValueError as exc:
        assert "slippage_bps" in str(exc)
    else:
        raise AssertionError("non-finite cost must be rejected")


def test_cost_gate_rejects_excessive_total_cost():
    gate = OpportunityCostGate(max_total_cost_bps=25.0)
    result = gate.evaluate(
        gross_edge_bps=100.0,
        fee_bps=10.0,
        spread_bps=5.0,
        slippage_bps=6.0,
        liquidity_bps=4.0,
        latency_bps=3.0,
    )
    assert result.viable is False
    assert result.reason == "costs exceed configured maximum"
