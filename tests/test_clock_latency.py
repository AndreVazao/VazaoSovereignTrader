from PC_ENGINE.market_events.clock_latency import ClockLatencyCalibrator, ClockLatencySample


def sample(offset_ms: int, processing_ms: int = 2) -> ClockLatencySample:
    receive_wall_ns = 1_700_000_000_000_000_000 + offset_ms * 1_000_000
    receive_mono_ns = 10_000_000_000
    return ClockLatencySample(
        venue="binance",
        venue_ts_ms=1_700_000_000_000,
        local_receive_wall_ns=receive_wall_ns,
        local_receive_ns=receive_mono_ns,
        local_process_ns=receive_mono_ns + processing_ms * 1_000_000,
    )


def test_calibrator_reports_offset_percentiles_and_jitter():
    calibrator = ClockLatencyCalibrator()
    calibrator.extend([sample(4), sample(6), sample(5), sample(7), sample(5)])
    stats = calibrator.stats("binance")
    assert stats is not None
    assert stats.samples == 5
    assert stats.median_offset_ms == 5
    assert stats.p95_offset_ms > 6
    assert stats.p99_offset_ms > stats.p95_offset_ms
    assert stats.jitter_ms == 0


def test_calibrator_reports_processing_delay():
    calibrator = ClockLatencyCalibrator()
    calibrator.extend([sample(3, 1), sample(3, 3), sample(3, 5)])
    stats = calibrator.stats("binance")
    assert stats is not None
    assert stats.median_processing_ms == 3


def test_calibrator_keeps_venues_separate():
    calibrator = ClockLatencyCalibrator()
    calibrator.add(sample(5))
    calibrator.add(
        ClockLatencySample(
            venue="okx",
            venue_ts_ms=1_700_000_000_000,
            local_receive_wall_ns=1_700_000_000_008_000_000,
            local_receive_ns=20_000_000_000,
            local_process_ns=20_002_000_000,
        )
    )
    assert calibrator.venues() == ("binance", "okx")
    assert calibrator.stats("okx").median_offset_ms == 8


def test_invalid_processing_order_is_rejected():
    calibrator = ClockLatencyCalibrator()
    try:
        calibrator.add(
            ClockLatencySample(
                venue="binance",
                venue_ts_ms=1_700_000_000_000,
                local_receive_wall_ns=1_700_000_000_000_000_000,
                local_receive_ns=10,
                local_process_ns=9,
            )
        )
        assert False, "expected ValueError"
    except ValueError:
        pass
