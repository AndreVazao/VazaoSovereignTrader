from __future__ import annotations

from PC_ENGINE.research.websocket_timing_validation import validate_websocket_timing


def _events():
    return [
        {"exchange": "binance", "symbol": "BTC/USDT", "exchange_ts_ms": 1000, "local_ts_ms": 1010, "local_receive_latency_ms": 10, "price": 100, "quantity": 1},
        {"exchange": "binance", "symbol": "BTC/USDT", "exchange_ts_ms": 2000, "local_ts_ms": 2012, "local_receive_latency_ms": 12, "price": 101, "quantity": 1},
    ]


def test_timing_validation_passes_clean_sample():
    lead = [
        {"exchange_lag_ms": 20, "receive_lag_ms": 22},
        {"exchange_lag_ms": 30, "receive_lag_ms": 31},
    ]
    report = validate_websocket_timing(_events(), lead, min_samples=2)
    assert report["paper_only"] is True
    assert report["eligible_for_economic_interpretation"] is True
    assert report["gates"]["timestamp_quality"] is True
    assert report["gates"]["lead_lag_quality"] is True


def test_negative_latency_blocks_economic_interpretation():
    events = _events()
    events[1]["local_ts_ms"] = 1900
    events[1]["local_receive_latency_ms"] = -100
    report = validate_websocket_timing(events, [], min_samples=2)
    assert report["eligible_for_economic_interpretation"] is False
    assert report["events"]["negative_latency"] == 1


def test_unknown_latency_stays_unknown_and_blocks_economic_interpretation():
    events = _events()
    for event in events:
        event["local_receive_latency_ms"] = None
    lead = [
        {"exchange_lag_ms": 20, "receive_lag_ms": 22},
        {"exchange_lag_ms": 30, "receive_lag_ms": 31},
    ]
    report = validate_websocket_timing(events, lead, min_samples=2)
    assert report["gates"]["timestamp_quality"] is True
    assert report["gates"]["receive_latency_quality"] is False
    assert report["events"]["unknown_receive_latency"] == 2
    assert report["eligible_for_economic_interpretation"] is False


def test_exchange_and_local_clock_domains_are_not_subtracted_for_latency():
    events = _events()
    events[1]["local_ts_ms"] = 1900
    events[1]["local_receive_latency_ms"] = 12
    lead = [
        {"exchange_lag_ms": 20, "receive_lag_ms": 22},
        {"exchange_lag_ms": 30, "receive_lag_ms": 31},
    ]
    report = validate_websocket_timing(events, lead, min_samples=2)
    assert report["events"]["negative_latency"] == 0
    assert report["gates"]["receive_latency_quality"] is True


def test_lead_lag_timestamp_mismatch_blocks_gate():
    lead = [{"exchange_lag_ms": 900, "receive_lag_ms": 20}]
    report = validate_websocket_timing(_events(), lead, min_samples=1, max_lead_ms=750)
    assert report["eligible_for_economic_interpretation"] is False
    assert report["lead_lag"]["rejected_timestamp_pairs"] == 1



def test_empty_latency_statistics_are_unknown_not_zero():
    events = _events()
    for event in events:
        event["local_receive_latency_ms"] = None
    report = validate_websocket_timing(events, [], min_samples=2)
    latency = report["events"]["latency_ms"]
    assert latency == {
        "mean": None,
        "p50": None,
        "p95": None,
        "p99": None,
        "max": None,
    }
    assert report["events"]["unknown_receive_latency"] == 2
    assert report["gates"]["receive_latency_quality"] is False
    assert report["eligible_for_economic_interpretation"] is False


def test_empty_lead_lag_delta_statistics_are_unknown_not_zero():
    report = validate_websocket_timing(_events(), [], min_samples=2)
    assert report["lead_lag"]["exchange_vs_receive_lag_delta_ms"] == {
        "p95": None,
        "max": None,
    }
