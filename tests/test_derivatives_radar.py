from PC_ENGINE.radar.derivatives_radar import DerivativeSnapshot, DerivativesRadar


def test_basis_is_calculated_in_bps():
    assert round(DerivativesRadar._basis_bps(101.0, 100.0), 4) == 100.0


def test_missing_derivatives_data_is_neutral():
    radar = DerivativesRadar()
    evidence = radar.evidence("BTC/USDT", 100.0, [])
    assert evidence.score == 0.0
    assert evidence.confidence == 0.0
    assert evidence.paper_only is True


def test_negative_funding_can_add_bullish_context():
    radar = DerivativesRadar()
    snapshots = [DerivativeSnapshot("binance", "BTC/USDT", -0.0005, 100.0, None, 100.0, 99.9, 10.01, 1)]
    evidence = radar.evidence("BTC/USDT", 100.0, snapshots)
    assert evidence.score > 0
    assert evidence.paper_only is True
