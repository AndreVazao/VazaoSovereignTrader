from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class L2ValidationRow:
    leader: str
    follower: str
    symbol: str
    direction: str
    in_samples: int
    out_samples: int
    in_expectancy: float
    out_expectancy: float
    out_ci_low: float
    out_ci_high: float
    out_completion_rate: float
    out_average_entry_impact_bps: float | None
    out_average_exit_impact_bps: float | None
    stable: bool


class L2OutOfSampleValidator:
    """Validate executable L2 replay results with a temporal 70/30 split.

    This validates replay evidence only. It does not authorize live trading.
    """

    def __init__(
        self,
        replay_path: str = "PC_ENGINE/data/replay/l2_temporal_replay.json",
        output_path: str = "PC_ENGINE/data/radar/l2_oos_validation.json",
        split_ratio: float = 0.70,
        min_in_samples: int = 30,
        min_out_samples: int = 20,
        min_completion_rate: float = 0.55,
    ) -> None:
        self.replay_path = Path(replay_path)
        self.output_path = Path(output_path)
        self.split_ratio = min(0.9, max(0.5, float(split_ratio)))
        self.min_in_samples = max(1, int(min_in_samples))
        self.min_out_samples = max(1, int(min_out_samples))
        self.min_completion_rate = min(1.0, max(0.0, float(min_completion_rate)))

    @staticmethod
    def _ci(values: list[float]) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        if len(values) < 2:
            return values[0], values[0]
        mean = statistics.fmean(values)
        margin = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
        return mean - margin, mean + margin

    def validate(self) -> list[L2ValidationRow]:
        if not self.replay_path.exists():
            return []
        try:
            payload = json.loads(self.replay_path.read_text(encoding="utf-8"))
            trades = payload.get("trades", [])
        except (OSError, json.JSONDecodeError, TypeError):
            trades = []

        # Keep every generated signal in the validation population. Filtering to
        # completed trades would create survivorship/selection bias and inflate
        # completion and expectancy by silently removing misses/rejections.
        valid = [
            t for t in trades
            if isinstance(t.get("signal_time_ms"), (int, float))
        ]
        valid.sort(key=lambda t: float(t["signal_time_ms"]))
        if not valid:
            return []

        split_index = max(1, min(len(valid) - 1, int(len(valid) * self.split_ratio)))
        split_time = float(valid[split_index]["signal_time_ms"])
        buckets: dict[tuple[str, str, str, str], dict[str, list[dict]]] = {}
        for trade in valid:
            key = (
                str(trade.get("leader", "")),
                str(trade.get("follower", "")),
                str(trade.get("symbol", "")),
                str(trade.get("direction", "")).upper(),
            )
            buckets.setdefault(key, {"in": [], "out": []})[
                "in" if float(trade["signal_time_ms"]) < split_time else "out"
            ].append(trade)

        rows: list[L2ValidationRow] = []
        for (leader, follower, symbol, direction), parts in buckets.items():
            inside, outside = parts["in"], parts["out"]
            if not inside or not outside:
                continue
            # A non-completed signal contributes zero realized P&L rather than
            # disappearing from the denominator.
            in_values = [
                float(t.get("net_pnl", 0.0) or 0.0)
                if t.get("status") in {"COMPLETED", "PARTIAL_EXIT"} and float(t.get("exit_filled_qty", 0) or 0) > 0
                else 0.0
                for t in inside
            ]
            out_values = [
                float(t.get("net_pnl", 0.0) or 0.0)
                if t.get("status") in {"COMPLETED", "PARTIAL_EXIT"} and float(t.get("exit_filled_qty", 0) or 0) > 0
                else 0.0
                for t in outside
            ]
            lo, hi = self._ci(out_values)
            completion = sum(
                t.get("status") == "COMPLETED"
                and float(t.get("exit_filled_qty", 0) or 0) >= float(t.get("entry_filled_qty", 0) or 0) > 0
                for t in outside
            ) / len(outside)
            entry_impacts = [
                float(t["entry_impact_bps"]) for t in outside
                if t.get("status") in {"COMPLETED", "PARTIAL_EXIT"} and t.get("entry_impact_bps") is not None
            ]
            exit_impacts = [
                float(t["exit_impact_bps"]) for t in outside
                if t.get("status") in {"COMPLETED", "PARTIAL_EXIT"} and t.get("exit_impact_bps") is not None
            ]
            stable = (
                len(inside) >= self.min_in_samples
                and len(outside) >= self.min_out_samples
                and statistics.fmean(in_values) > 0
                and statistics.fmean(out_values) > 0
                and lo > 0
                and completion >= self.min_completion_rate
            )
            rows.append(L2ValidationRow(
                leader, follower, symbol, direction,
                len(inside), len(outside),
                round(statistics.fmean(in_values), 8),
                round(statistics.fmean(out_values), 8),
                round(lo, 8), round(hi, 8),
                round(completion, 6),
                round(statistics.fmean(entry_impacts), 4) if entry_impacts else None,
                round(statistics.fmean(exit_impacts), 4) if exit_impacts else None,
                stable,
            ))

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps({
            "generated_at_ms": time.time_ns() // 1_000_000,
            "paper_only": True,
            "split_ratio": self.split_ratio,
            "split_timestamp_ms": split_time,
            "min_in_samples": self.min_in_samples,
            "min_out_samples": self.min_out_samples,
            "min_completion_rate": self.min_completion_rate,
            "rows": [asdict(row) for row in rows],
        }, indent=2), encoding="utf-8")
        return rows
