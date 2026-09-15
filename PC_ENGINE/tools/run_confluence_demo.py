from __future__ import annotations

import json

from PC_ENGINE.core.confluence import ConfluenceEngine
from PC_ENGINE.radar.lead_lag_signal import PaperLeadLagSignal
from PC_ENGINE.radar.regime_engine import MarketRegime


def main() -> None:
    engine = ConfluenceEngine()
    result = engine.evaluate(
        symbol="BTC/USDT",
        technical_action="BUY",
        technical_strength=0.78,
        pattern_bias=0.65,
        radar_pressure=0.55,
        lead_lag_signals=[
            PaperLeadLagSignal("BTC/USDT", "okx", "binance", "UP", 500, 8.2, 0.91, 250),
        ],
        regime=MarketRegime("UP_NORMAL", "UP", "NORMAL", 0.9),
    )
    print(json.dumps({"confluence": result.__dict__}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
