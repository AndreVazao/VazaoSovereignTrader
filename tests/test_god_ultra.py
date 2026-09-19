from PC_ENGINE.autonomy.god_ultra import GodUltraEngine, Opportunity, RiskSnapshot


def make_opp(i: int, edge: float, capital: float = 20.0, group: str | None = None, metadata=None) -> Opportunity:
    return Opportunity(
        opportunity_id=f"opp-{i}", venue=f"venue-{i}", symbol="BTC/USDT",
        side="BUY", expected_edge_bps=edge, confidence=0.9, signal_age_ms=50,
        required_capital=capital, liquidity_capital=capital,
        validated=True, out_of_sample=True,
        independent_group=group or f"group-{i}", metadata=metadata or {},
    )


def test_selects_multiple_independent_opportunities():
    engine = GodUltraEngine(max_parallel_orders=4, reserve_cash_pct=0.2, max_single_opportunity_pct=0.5)
    risk = RiskSnapshot(available_capital=100.0, max_exposure=80.0)
    intents = engine.select([make_opp(1, 8), make_opp(2, 6), make_opp(3, 5)], risk)
    assert len(intents) == 3
    assert sum(i.capital for i in intents) == 60


def test_does_not_execute_unvalidated_opportunity():
    engine = GodUltraEngine()
    risk = RiskSnapshot(available_capital=100.0, max_exposure=80.0)
    bad = make_opp(1, 10)
    bad = Opportunity(**{**bad.__dict__, "validated": False})
    assert engine.select([bad], risk) == []


def test_kill_switch_blocks_everything():
    engine = GodUltraEngine()
    risk = RiskSnapshot(available_capital=100.0, max_exposure=80.0, kill_switch=True)
    assert engine.select([make_opp(1, 10)], risk) == []


def test_execution_quality_gates_block_bad_l2():
    engine = GodUltraEngine(max_execution_impact_bps=10.0, min_fill_ratio=0.95, max_book_age_ms=100.0)
    risk = RiskSnapshot(available_capital=100.0, max_exposure=80.0)
    bad = make_opp(1, 10, metadata={"execution_impact_bps": 12, "fill_ratio": 1.0, "book_age_ms": 10})
    assert engine.select([bad], risk) == []


def test_execution_quality_gates_accept_good_l2():
    engine = GodUltraEngine(max_execution_impact_bps=10.0, min_fill_ratio=0.95, max_book_age_ms=100.0)
    risk = RiskSnapshot(available_capital=100.0, max_exposure=80.0)
    good = make_opp(1, 10, metadata={"execution_impact_bps": 4, "fill_ratio": 1.0, "book_age_ms": 10})
    assert len(engine.select([good], risk)) == 1
