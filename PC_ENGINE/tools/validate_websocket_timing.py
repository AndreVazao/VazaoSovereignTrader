from __future__ import annotations

import argparse

from PC_ENGINE.research.websocket_timing_validation import validate_paths, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public WebSocket timestamps for PAPER research.")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--output", default="PC_ENGINE/data/radar/websocket_timing_validation.json")
    parser.add_argument("--max-receive-latency-ms", type=int, default=2000)
    parser.add_argument("--max-lead-ms", type=int, default=750)
    parser.add_argument("--min-samples", type=int, default=100)
    args = parser.parse_args()
    report = validate_paths(
        args.data_dir,
        max_receive_latency_ms=args.max_receive_latency_ms,
        max_lead_ms=args.max_lead_ms,
        min_samples=args.min_samples,
    )
    write_report(report, args.output)
    print(f"WebSocket timing validation: eligible={report['eligible_for_economic_interpretation']}")
    print(report["interpretation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
