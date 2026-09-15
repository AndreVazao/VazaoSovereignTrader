from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PC_ENGINE.core.confluence import ConfluenceScore


@dataclass(frozen=True)
class ConfluenceObservation:
    ts_ms: int
    symbol: str
    price: float
    action: str
    score: float
    confidence: float
    horizon_ms: int
    paper_only: bool = True


class PaperConfluenceTracker:
    """Records confluence observations and later scores their realized outcome.

    This is deliberately separate from order execution. It lets the project
    measure whether stronger confluence actually predicts future movement
    after estimated round-trip costs.
    """

    def __init__(self, data_dir: str | Path = "PC_ENGINE/data/radar", horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000)):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.horizons_ms = tuple(int(x) for x in horizons_ms if int(x) > 0)
        self.observation_path = self.data_dir / "confluence_observations.jsonl"
        self.outcome_path = self.data_dir / "confluence_outcomes.jsonl"

    def record(self, symbol: str, price: float, score: ConfluenceScore) -> None:
        if price <= 0:
            return
        now = int(time.time() * 1000)
        with self.observation_path.open("a", encoding="utf-8") as handle:
            for horizon in self.horizons_ms:
                row = ConfluenceObservation(now, symbol, float(price), score.action, score.score, score.confidence, horizon)
                handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")

    @staticmethod
    def _read(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except json.JSONDecodeError:
                continue
        return rows

    def observations(self) -> list[dict[str, Any]]:
        return self._read(self.observation_path)

    def record_outcome(self, observation: dict[str, Any], future_price: float, fee_bps_round_trip: float = 28.0) -> dict[str, Any] | None:
        if future_price <= 0 or float(observation.get("price", 0.0)) <= 0:
            return None
        entry = float(observation["price"])
        raw_return_bps = (future_price - entry) / entry * 10000.0
        direction = 1.0 if observation.get("action") == "BUY" else -1.0 if observation.get("action") == "SELL" else 0.0
        directional_bps = raw_return_bps * direction
        net_bps = directional_bps - float(fee_bps_round_trip)
        outcome = {
            **observation,
            "future_price": float(future_price),
            "raw_return_bps": round(raw_return_bps, 4),
            "directional_bps": round(directional_bps, 4),
            "net_bps": round(net_bps, 4),
            "profitable_after_costs": bool(direction != 0 and net_bps > 0),
            "evaluated_ts_ms": int(time.time() * 1000),
        }
        with self.outcome_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(outcome, ensure_ascii=False) + "\n")
        return outcome

    def summary(self) -> dict[str, Any]:
        rows = self._read(self.outcome_path)
        grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
        for row in rows:
            key = (str(row.get("symbol", "")), int(row.get("horizon_ms", 0)), str(row.get("action", "HOLD")))
            grouped.setdefault(key, []).append(row)
        stats = []
        for (symbol, horizon, action), values in grouped.items():
            nets = [float(x.get("net_bps", 0.0)) for x in values]
            wins = sum(1 for x in values if x.get("profitable_after_costs"))
            mean_net = sum(nets) / len(nets) if nets else 0.0
            stats.append({
                "symbol": symbol,
                "horizon_ms": horizon,
                "action": action,
                "samples": len(values),
                "wins": wins,
                "win_rate": round(wins / len(values), 4) if values else 0.0,
                "mean_net_bps": round(mean_net, 4),
            })
        stats.sort(key=lambda x: (x["mean_net_bps"], x["samples"]), reverse=True)
        return {"generated_ts_ms": int(time.time() * 1000), "stats": stats}
