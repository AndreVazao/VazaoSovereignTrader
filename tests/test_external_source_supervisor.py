from __future__ import annotations

import unittest

from PC_ENGINE.radar.external_source_adapter import ExternalMarketObservation
from PC_ENGINE.radar.external_source_supervisor import ExternalSourceSupervisor


class FakeRadar:
    def __init__(self) -> None:
        self.rows = []

    def ingest_external_observation(self, observation):
        self.rows.append(observation)


class FakeAdapter:
    source_id = "feed-a"

    def __init__(self, rows):
        self.rows = rows

    def poll(self):
        return self.rows


class ExternalSourceSupervisorTests(unittest.TestCase):
    def test_poll_normalizes_and_tracks_health(self) -> None:
        radar = FakeRadar()
        adapter = FakeAdapter([
            ExternalMarketObservation(
                source_id="feed-a",
                symbol="BTC/USDT",
                price=100.0,
                source_ts_ms=1_000,
                received_ts_ms=1_025,
                sequence=3,
            )
        ])
        supervisor = ExternalSourceSupervisor(
            radar,
            [adapter],
            clock_ms=lambda: 2_000,
        )

        accepted = supervisor.poll_once()

        self.assertEqual(accepted, 1)
        self.assertEqual(len(radar.rows), 1)
        health = supervisor.snapshot()["sources"]["feed-a"]
        self.assertEqual(health["accepted"], 1)
        self.assertEqual(health["rejected"], 0)
        self.assertEqual(health["last_transport_latency_ms"], 25.0)
        self.assertEqual(health["last_sequence"], 3)
        self.assertTrue(health["healthy"])

    def test_stale_source_is_not_healthy(self) -> None:
        radar = FakeRadar()
        adapter = FakeAdapter([
            ExternalMarketObservation(
                source_id="feed-a",
                symbol="BTC/USDT",
                price=100.0,
                source_ts_ms=1_000,
                received_ts_ms=1_000,
            )
        ])
        supervisor = ExternalSourceSupervisor(
            radar,
            [adapter],
            max_silence_seconds=1,
            clock_ms=lambda: 3_000,
        )
        supervisor.poll_once()
        health = supervisor.snapshot()["sources"]["feed-a"]
        self.assertFalse(health["fresh"])
        self.assertFalse(health["healthy"])
        self.assertEqual(health["last_observation_age_ms"], 2000)

    def test_invalid_row_is_rejected_without_stopping_other_sources(self) -> None:
        radar = FakeRadar()
        bad = FakeAdapter([
            ExternalMarketObservation(
                source_id="feed-a",
                symbol="BTC/USDT",
                price=100.0,
                source_ts_ms=1_000,
                direction="BUY",
            )
        ])
        good = FakeAdapter([
            ExternalMarketObservation(
                source_id="feed-b",
                symbol="BTC/USDT",
                price=101.0,
                source_ts_ms=1_000,
            )
        ])
        supervisor = ExternalSourceSupervisor(radar, [bad, good])

        accepted = supervisor.poll_once()

        self.assertEqual(accepted, 1)
        self.assertEqual(len(radar.rows), 1)
        snapshot = supervisor.snapshot()
        self.assertEqual(snapshot["sources"]["feed-a"]["rejected"], 1)
        self.assertEqual(snapshot["sources"]["feed-b"]["accepted"], 1)

    def test_adapter_failure_is_isolated(self) -> None:
        class Broken:
            source_id = "broken"

            def poll(self):
                raise RuntimeError("boom")

        radar = FakeRadar()
        supervisor = ExternalSourceSupervisor(radar, [Broken()])
        self.assertEqual(supervisor.poll_once(), 0)
        health = supervisor.snapshot()["sources"]["broken"]
        self.assertEqual(health["errors"], 1)
        self.assertEqual(health["last_error"], "boom")


if __name__ == "__main__":
    unittest.main()
