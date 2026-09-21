from __future__ import annotations

import unittest

from PC_ENGINE.radar.external_source_adapter import (
    ExternalMarketObservation,
    observation_quality,
    validate_observation,
)


class ExternalSourceAdapterContractTests(unittest.TestCase):
    def test_valid_observation_has_transport_quality(self) -> None:
        observation = ExternalMarketObservation(
            source_id="official-feed",
            symbol="BTC/USDT",
            price=100.0,
            source_ts_ms=1_000,
            direction="UP",
            received_ts_ms=1_025,
        )
        validate_observation(observation)
        quality = observation_quality(observation)
        self.assertTrue(quality["timestamp_valid"])
        self.assertEqual(quality["transport_latency_ms"], 25.0)
        self.assertTrue(quality["clock_order_valid"])

    def test_invalid_observation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_observation(
                ExternalMarketObservation(
                    source_id="",
                    symbol="BTC/USDT",
                    price=100.0,
                    source_ts_ms=1_000,
                )
            )

    def test_invalid_direction_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_observation(
                ExternalMarketObservation(
                    source_id="feed",
                    symbol="BTC/USDT",
                    price=100.0,
                    source_ts_ms=1_000,
                    direction="BUY",
                )
            )


if __name__ == "__main__":
    unittest.main()
