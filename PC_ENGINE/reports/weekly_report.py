from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PC_ENGINE.core.config import DATA_DIR


class WeeklyReporter:
    def __init__(self, out_dir: Path | None = None):
        self.out_dir = out_dir or (DATA_DIR / "reports")
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def summarize(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_symbol = defaultdict(float)
        wins = losses = 0
        total = 0.0
        worst = 0.0
        best = 0.0
        for trade in trades:
            pnl = float(trade.get("pnl_pct", 0.0))
            symbol = trade.get("symbol", "UNKNOWN")
            by_symbol[symbol] += pnl
            total += pnl
            best = max(best, pnl)
            worst = min(worst, pnl)
            if pnl >= 0:
                wins += 1
            else:
                losses += 1
        count = wins + losses
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "trades": count,
            "wins": wins,
            "losses": losses,
            "winrate": wins / count if count else 0.0,
            "pnl_pct": total,
            "best_trade_pct": best,
            "worst_trade_pct": worst,
            "by_symbol": dict(by_symbol),
        }

    def write(self, week_key: str, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = self.summarize(trades)
        json_path = self.out_dir / f"weekly_report_{week_key}.json"
        csv_path = self.out_dir / f"weekly_report_{week_key}.csv"
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            for key, value in summary.items():
                if key != "by_symbol":
                    writer.writerow([key, value])
            for symbol, pnl in summary["by_symbol"].items():
                writer.writerow([f"symbol_{symbol}_pnl_pct", pnl])
        return summary
