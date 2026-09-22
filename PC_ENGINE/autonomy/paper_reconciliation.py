from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


class PaperAutonomyReconciler:
    """Reconcile autonomous PAPER intents against recorded paper fills/runs.

    This is accounting/observability only. It never authorizes or submits orders.
    """

    def __init__(
        self,
        intents_path: str = "PC_ENGINE/data/paper/autonomous_intents.jsonl",
        fills_path: str = "PC_ENGINE/data/paper/fills.jsonl",
        runs_path: str = "PC_ENGINE/data/paper/runs.jsonl",
        output_path: str = "PC_ENGINE/data/paper/autonomous_reconciliation.json",
    ):
        self.intents_path = Path(intents_path)
        self.fills_path = Path(fills_path)
        self.runs_path = Path(runs_path)
        self.output_path = Path(output_path)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    rows.append(value)
        except OSError:
            return []
        return rows

    @staticmethod
    def _read_runs(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        except (OSError, json.JSONDecodeError):
            pass
        return PaperAutonomyReconciler._read_jsonl(path)

    def reconcile(self) -> dict[str, Any]:
        intents = self._read_jsonl(self.intents_path)
        fills = self._read_jsonl(self.fills_path)
        runs = self._read_runs(self.runs_path)

        fills_by_opp: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for fill in fills:
            fills_by_opp[str(fill.get("opportunity_id", ""))].append(fill)

        intent_rows = []
        reconciled = 0
        missing = 0
        rejected = 0
        partial = 0
        completed = 0
        invalid = 0
        signed_notional = 0.0
        filled_notional = 0.0
        fees = 0.0

        for intent in intents:
            opportunity_id = str(intent.get("opportunity_id", ""))
            matched = fills_by_opp.get(opportunity_id, [])
            requested_values = [float(x.get("requested_qty", 0.0) or 0.0) for x in matched]
            requested = max(requested_values, default=0.0)
            filled = sum(float(x.get("filled_qty", 0.0) or 0.0) for x in matched)
            fee = sum(float(x.get("fee", 0.0) or 0.0) for x in matched)
            notional = sum(
                float(x.get("filled_qty", 0.0) or 0.0)
                * float(x.get("fill_price", x.get("requested_price", 0.0)) or 0.0)
                for x in matched
            )
            side = str(intent.get("side", "BUY")).upper()
            signed = notional if side == "BUY" else -notional
            statuses = {str(x.get("status", "")).upper() for x in matched}
            fill_ids = [str(x.get("fill_id", "")).strip() for x in matched]
            duplicate_fill_ids = len(fill_ids) != len(set(x for x in fill_ids if x))
            invalid_values = any(
                float(x.get("filled_qty", 0.0) or 0.0) < 0
                or float(x.get("fee", 0.0) or 0.0) < 0
                or float(x.get("fill_price", x.get("requested_price", 0.0)) or 0.0) < 0
                for x in matched
            )
            overfill = requested > 0 and filled > requested + max(1e-12, requested * 1e-9)

            if not matched:
                state = "MISSING"
                missing += 1
            elif duplicate_fill_ids or invalid_values or overfill:
                state = "INVALID"
                invalid += 1
            elif "REJECTED" in statuses or "INVALID" in statuses:
                state = "REJECTED"
                rejected += 1
            elif filled + max(1e-12, requested * 1e-9) < requested:
                state = "PARTIAL"
                partial += 1
                reconciled += 1
            else:
                state = "FILLED"
                completed += 1
                reconciled += 1

            signed_notional += signed
            filled_notional += notional
            fees += fee
            intent_rows.append({
                "intent_id": str(intent.get("intent_id", "")),
                "opportunity_id": opportunity_id,
                "venue": str(intent.get("venue", "")),
                "symbol": str(intent.get("symbol", "")),
                "side": side,
                "state": state,
                "requested_qty": requested,
                "filled_qty": filled,
                "fill_ratio": (filled / requested) if requested > 0 else 0.0,
                "filled_notional": notional,
                "fees": fee,
                "fill_ids": [str(x.get("fill_id", "")) for x in matched],
            })

        gross_pnl = sum(float(run.get("gross_pnl", 0.0) or 0.0) for run in runs)
        run_fees = sum(float(run.get("fees", 0.0) or 0.0) for run in runs)
        net_pnl = sum(float(run.get("net_pnl", 0.0) or 0.0) for run in runs)
        drawdown = min(0.0, net_pnl)

        payload = {
            "generated_at": time.time(),
            "mode": "PAPER",
            "safe_for_live": False,
            "status": "RECONCILED" if intents else "NO_INTENTS",
            "intents": len(intents),
            "reconciled_intents": reconciled,
            "missing_intents": missing,
            "rejected_intents": rejected,
            "partial_intents": partial,
            "invalid_intents": invalid,
            "completed_intents": completed,
            "fills": len(fills),
            "runs": len(runs),
            "requested_notional": sum(float(x.get("required_capital", 0.0) or 0.0) for x in intents),
            "filled_notional": filled_notional,
            "net_signed_notional": signed_notional,
            "fees_from_fills": fees,
            "gross_pnl": gross_pnl,
            "run_fees": run_fees,
            "net_pnl": net_pnl,
            "conservative_drawdown_floor": drawdown,
            "unreconciled_ratio": ((missing + invalid) / len(intents)) if intents else 0.0,
            "rows": intent_rows,
        }
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
