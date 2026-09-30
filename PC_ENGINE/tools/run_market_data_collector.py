from __future__ import annotations

import argparse
import json
import signal
import threading
import time
from pathlib import Path

from PC_ENGINE.radar.hot_path import HotPathLeadLagEngine, HotPathOpportunity
from PC_ENGINE.radar.hot_path_outcomes import HotPathOutcomeTracker
from PC_ENGINE.radar.hot_path_calibration import write_hot_path_calibration
from PC_ENGINE.radar.lead_lag_learning import LeadLagLearningEngine
from PC_ENGINE.radar.websocket_radar import WebSocketMarketRadar
from PC_ENGINE.research.paper_study import load_states, run_study, write_report
from PC_ENGINE.research.websocket_timing_validation import validate_paths, write_report as write_timing_report


REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run continuous public market-data collection and PAPER learning."
    )
    parser.add_argument(
        "--config",
        default=str(REPO_ROOT / "PC_ENGINE" / "config" / "config.local.json"),
    )
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--learn-minutes", type=float, default=5.0)
    parser.add_argument("--study-minutes", type=float, default=None)
    args = parser.parse_args()

    config = _load_config(_resolve_path(args.config))
    radar_cfg = config.get("radar", {})
    symbols = list(radar_cfg.get("websocket_symbols") or config.get("symbols") or ["BTC/USDT", "ETH/USDT"])
    exchanges = list(radar_cfg.get("websocket_exchanges") or ["binance", "coinbase", "okx"])
    data_dir = _resolve_path(args.data_dir or radar_cfg.get("data_dir") or "PC_ENGINE/data/radar")
    data_dir.mkdir(parents=True, exist_ok=True)
    health_path = data_dir / "market_data_health.json"

    def write_health(status: str, **extra) -> None:
        payload = {
            "service": "market_data_collector",
            "status": status,
            "timestamp_ms": time.time_ns() // 1_000_000,
            "symbols": symbols,
            "exchanges": exchanges,
            "data_dir": str(data_dir),
            "paper_only": True,
            **extra,
        }
        tmp = health_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        tmp.replace(health_path)

    stop = threading.Event()

    def shutdown(_signum, _frame) -> None:
        stop.set()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    hot_path = HotPathLeadLagEngine(
        exchanges=exchanges,
        lead_window_ms=int(radar_cfg.get("lead_window_ms", 750)),
        stale_after_ms=int(radar_cfg.get("hot_path_stale_after_ms", 750)),
        min_move_bps=float(radar_cfg.get("min_move_bps", 5)),
        min_expected_net_bps=float(radar_cfg.get("hot_path_min_expected_net_bps", 2)),
        fee_bps_round_trip=float(radar_cfg.get("lead_lag_fee_bps_per_side", 10)) * 2,
        slippage_bps_round_trip=float(radar_cfg.get("lead_lag_slippage_bps_per_side", 4)) * 2,
        latency_bps_per_100ms=float(radar_cfg.get("hot_path_latency_bps_per_100ms", 0.5)),
        horizon_ms=int(radar_cfg.get("hot_path_horizon_ms", 500)),
        data_dir=data_dir,
    )
    opportunity_queue: list[HotPathOpportunity] = []
    opportunity_lock = threading.Lock()
    outcome_tracker = HotPathOutcomeTracker(
        max_pending=int(radar_cfg.get("hot_path_max_pending_outcomes", 4096))
    )
    outcomes_path = data_dir / "hot_path_outcomes.jsonl"

    def on_market_event(event) -> None:
        # Callback stays memory-only: no disk I/O, blocking research, or orders.
        outcome_tracker.on_market_event(event)
        opportunity = hot_path.on_market_event(event)
        if opportunity is not None:
            outcome_tracker.register(opportunity)
            with opportunity_lock:
                opportunity_queue.append(opportunity)
                if len(opportunity_queue) > 256:
                    del opportunity_queue[:-256]

    radar = WebSocketMarketRadar(
        symbols=symbols,
        exchanges=exchanges,
        data_dir=data_dir,
        min_move_bps=float(radar_cfg.get("min_move_bps", 5)),
        lead_window_ms=int(radar_cfg.get("lead_window_ms", 750)),
        callback=on_market_event,
    )
    learner = LeadLagLearningEngine(
        data_dir=data_dir,
        min_samples=int(radar_cfg.get("lead_lag_min_samples", 100)),
        fee_bps_per_side=float(radar_cfg.get("lead_lag_fee_bps_per_side", 10)),
        slippage_bps_per_side=float(radar_cfg.get("lead_lag_slippage_bps_per_side", 4)),
        response_threshold_bps=float(radar_cfg.get("lead_lag_response_threshold_bps", 2)),
    )

    radar.start()
    write_health(
        "RUNNING",
        radar=radar.snapshot(),
        hot_path=hot_path.snapshot(),
        hot_path_outcomes=outcome_tracker.snapshot(),
    )
    print(json.dumps({
        "service": "market_data_collector",
        "status": "RUNNING",
        "symbols": symbols,
        "exchanges": exchanges,
        "data_dir": str(data_dir),
        "paper_only": True,
    }, ensure_ascii=False), flush=True)

    study_cfg = dict(config.get("paper_study", {}))
    study_enabled = bool(study_cfg.get("enabled", True))
    study_minutes = float(args.study_minutes if args.study_minutes is not None else study_cfg.get("interval_minutes", 15))
    next_learning = 0.0
    next_study = 0.0
    try:
        while not stop.is_set():
            now = time.monotonic()
            if now >= next_learning:
                stats = learner.learn()
                calibration = write_hot_path_calibration(
                    outcomes_path,
                    data_dir / "hot_path_calibration.json",
                    min_samples=int(radar_cfg.get("hot_path_calibration_min_samples", 100)),
                )
                for row in stats:
                    if row.eligible:
                        hot_path.set_expectancy(
                            symbol=row.symbol,
                            leader=row.leader,
                            follower=row.follower,
                            direction=row.direction,
                            expected_response_bps=row.expectancy_bps,
                        )
                radar_state = radar.snapshot()
                write_health(
                    "RUNNING",
                    radar=radar_state,
                    learning={
                        "stats": len(stats),
                        "eligible_paper_relationships": sum(1 for row in stats if row.eligible),
                    },
                    hot_path_calibration={
                        "outcome_samples": calibration["outcome_samples"],
                        "relationships": calibration["relationships"],
                        "paper_only": True,
                        "execution_authorized": False,
                    },
                )
                print(json.dumps({
                    "service": "market_data_collector",
                    "stats": len(stats),
                    "eligible_paper_relationships": sum(1 for row in stats if row.eligible),
                    "hot_path_outcome_samples": calibration["outcome_samples"],
                    "hot_path_calibration_relationships": calibration["relationships"],
                    "timestamp_ms": time.time_ns() // 1_000_000,
                }, ensure_ascii=False), flush=True)
                next_learning = now + max(30.0, args.learn_minutes * 60.0)
            with opportunity_lock:
                queued = list(opportunity_queue)
                opportunity_queue.clear()
            for opportunity in queued:
                hot_path.persist(opportunity)
            completed_outcomes = outcome_tracker.drain_completed()
            if completed_outcomes:
                with outcomes_path.open("a", encoding="utf-8") as handle:
                    for outcome in completed_outcomes:
                        handle.write(json.dumps(outcome, ensure_ascii=False, sort_keys=True) + "\n")

            if study_enabled and now >= next_study:
                states_path = data_dir / str(study_cfg.get("states_filename", "market_states.jsonl"))
                report_path = data_dir / str(study_cfg.get("report_filename", "paper_study_report.json"))
                timing_path = data_dir / str(study_cfg.get("timing_report_filename", "websocket_timing_validation.json"))
                try:
                    states = load_states(states_path, limit=int(study_cfg.get("max_states", 100000)))
                    report = run_study(
                        states,
                        horizon_ms=int(study_cfg.get("horizon_ms", 5000)),
                        cost_bps=float(study_cfg.get("cost_bps", 28.0)),
                        folds=int(study_cfg.get("walk_forward_folds", 5)),
                        min_train=int(study_cfg.get("walk_forward_min_train", 100)),
                        test_size=int(study_cfg.get("walk_forward_test_size", 50)),
                        monte_carlo_iterations=int(study_cfg.get("monte_carlo_iterations", 2000)),
                    )
                    write_report(report, report_path)
                    timing = validate_paths(
                        data_dir,
                        max_receive_latency_ms=int(study_cfg.get("max_receive_latency_ms", 2000)),
                        max_lead_ms=int(radar_cfg.get("lead_window_ms", 750)),
                        min_samples=int(study_cfg.get("timing_min_samples", 100)),
                    )
                    write_timing_report(timing, timing_path)
                    write_health(
                        "RUNNING",
                        radar=radar.snapshot(),
                        hot_path=hot_path.snapshot(),
                        hot_path_outcomes=outcome_tracker.snapshot(),
                        study={
                            "enabled": True,
                            "state_samples": len(states),
                            "outcome_samples": report.get("outcome_samples", 0),
                            "timing_eligible": timing.get("eligible_for_economic_interpretation", False),
                            "report_path": str(report_path),
                            "timing_report_path": str(timing_path),
                        },
                    )
                except Exception as exc:
                    write_health(
                        "RUNNING",
                        radar=radar.snapshot(),
                        hot_path=hot_path.snapshot(),
                        hot_path_outcomes=outcome_tracker.snapshot(),
                        study={"enabled": True, "error": f"{type(exc).__name__}: {exc}"},
                    )
                next_study = now + max(60.0, study_minutes * 60.0)
            stop.wait(1.0)
    finally:
        radar.stop()
        learner.learn()
        completed_outcomes = outcome_tracker.drain_completed()
        if completed_outcomes:
            with outcomes_path.open("a", encoding="utf-8") as handle:
                for outcome in completed_outcomes:
                    handle.write(json.dumps(outcome, ensure_ascii=False, sort_keys=True) + "\n")
        write_health(
            "STOPPED",
            radar=radar.snapshot(),
            hot_path=hot_path.snapshot(),
            hot_path_outcomes=outcome_tracker.snapshot(),
        )
        print("Market-data collector stopped cleanly.", flush=True)


if __name__ == "__main__":
    main()
