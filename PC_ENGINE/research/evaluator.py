from __future__ import annotations

import json
import re
import statistics
from pathlib import Path


class ResearchOwnDataEvaluator:
    """Measure research hypotheses against the trader's own PAPER/L2 evidence.

    Research text is never converted into an order. The evaluator only reports
    measurable evidence and whether an existing OOS result is relevant.
    """

    def __init__(
        self,
        replay_path: str = "PC_ENGINE/data/replay/l2_temporal_replay.json",
        oos_path: str = "PC_ENGINE/data/radar/l2_oos_validation.json",
    ):
        self.replay_path = Path(replay_path)
        self.oos_path = Path(oos_path)

    @staticmethod
    def _read(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _tokens(message: str) -> set[str]:
        text = message.upper()
        aliases = {
            "BTC": "BTC/USDT", "ETH": "ETH/USDT", "SOL": "SOL/USDT",
            "BNB": "BNB/USDT", "DOGE": "DOGE/USDT",
            "BTC/USDT": "BTC/USDT", "ETH/USDT": "ETH/USDT",
            "SOL/USDT": "SOL/USDT", "BNB/USDT": "BNB/USDT",
            "DOGE/USDT": "DOGE/USDT",
        }
        return {value for key, value in aliases.items() if re.search(r"\b" + re.escape(key) + r"\b", text)}

    def evaluate(self, message: str) -> dict:
        replay = self._read(self.replay_path)
        oos = self._read(self.oos_path)
        trades = replay.get("trades", [])
        if not isinstance(trades, list):
            trades = []
        symbols = self._tokens(message)
        scoped = [t for t in trades if not symbols or str(t.get("symbol", "")).upper() in symbols]
        completed = [
            t for t in scoped
            if t.get("status") in {"COMPLETED", "PARTIAL_EXIT"} and float(t.get("exit_filled_qty", 0) or 0) > 0
        ]
        pnl = [float(t.get("net_pnl", 0.0) or 0.0) for t in completed]
        impacts = [
            float(t.get("entry_impact_bps", 0.0) or 0.0) + float(t.get("exit_impact_bps", 0.0) or 0.0)
            for t in completed
            if t.get("entry_impact_bps") is not None and t.get("exit_impact_bps") is not None
        ]
        completion = len(completed) / len(scoped) if scoped else 0.0

        oos_rows = oos.get("rows", []) if isinstance(oos, dict) else []
        relevant_oos = [
            row for row in oos_rows
            if row.get("stable") and (not symbols or str(row.get("symbol", "")).upper() in symbols)
        ]

        if not scoped:
            status = "INSUFFICIENT_DATA"
        elif len(completed) < 5:
            status = "MEASURED_INSUFFICIENT_SAMPLE"
        elif relevant_oos:
            status = "OOS_VALIDATION_CANDIDATE"
        else:
            status = "MEASURED"

        evidence_ids = [
            str(t.get("trade_id"))
            for t in completed[:20]
            if t.get("trade_id")
        ]
        metrics = {
            "symbols_scoped": sorted(symbols),
            "replay_samples": len(scoped),
            "completed_samples": len(completed),
            "completion_rate": round(completion, 6),
            "net_pnl_sum": round(sum(pnl), 8),
            "net_pnl_expectancy": round(statistics.fmean(pnl), 8) if pnl else 0.0,
            "positive_trade_rate": round(sum(x > 0 for x in pnl) / len(pnl), 6) if pnl else 0.0,
            "average_round_trip_impact_bps": round(statistics.fmean(impacts), 4) if impacts else None,
            "relevant_stable_oos_rows": len(relevant_oos),
        }
        return {
            "status": status,
            "metrics": metrics,
            "evidence_ids": evidence_ids,
            "data_sources": [str(self.replay_path), str(self.oos_path)],
            "summary": (
                f"Dados próprios: {len(scoped)} amostras, {len(completed)} completas, "
                f"completion={completion:.1%}, expectancy={metrics['net_pnl_expectancy']:.6f}, "
                f"OOS estável relevante={len(relevant_oos)}. Estado={status}."
            ),
        }
