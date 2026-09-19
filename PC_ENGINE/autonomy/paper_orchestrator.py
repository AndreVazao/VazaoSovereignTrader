from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from PC_ENGINE.autonomy.god_ultra import GodUltraEngine, Opportunity, RiskSnapshot


class PaperAutonomyOrchestrator:
    """Turn validated L2 evidence into PAPER execution intents.

    This is a batch bridge between validation and autonomous decisioning. It
    never places an exchange order and refuses incomplete evidence.
    """

    def __init__(
        self,
        validation_path: str = "PC_ENGINE/data/radar/l2_oos_validation.json",
        replay_path: str = "PC_ENGINE/data/replay/l2_temporal_replay.json",
        output_path: str = "PC_ENGINE/data/paper/autonomous_intents.jsonl",
    ):
        self.validation_path = Path(validation_path)
        self.replay_path = Path(replay_path)
        self.output_path = Path(output_path)

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def build_opportunities(self) -> list[Opportunity]:
        validation = self._read_json(self.validation_path)
        opportunities: list[Opportunity] = []
        for row in validation.get("rows", []):
            if not row.get("stable"):
                continue
            out_expectancy = float(row.get("out_expectancy", 0.0))
            ci_low = float(row.get("out_ci_low", 0.0))
            ci_high = float(row.get("out_ci_high", 0.0))
            completion = float(row.get("out_completion_rate", 0.0))
            impact = max(
                float(row.get("out_average_entry_impact_bps") or 0.0),
                float(row.get("out_average_exit_impact_bps") or 0.0),
            )
            ci_width = max(0.0, ci_high - ci_low)
            confidence = max(0.0, min(1.0, completion * (1.0 / (1.0 + ci_width))))
            opportunities.append(Opportunity(
                opportunity_id=f"l2-{row.get('leader')}-{row.get('follower')}-{row.get('symbol')}-{row.get('direction')}",
                venue=str(row.get("follower", "")),
                symbol=str(row.get("symbol", "")),
                side="BUY" if str(row.get("direction", "")).upper() == "UP" else "SELL",
                expected_edge_bps=max(0.0, out_expectancy),
                confidence=confidence,
                signal_age_ms=0.0,
                required_capital=100.0,
                liquidity_capital=100.0,
                validated=True,
                out_of_sample=True,
                independent_group=f"{row.get('leader')}->{row.get('follower')}:{row.get('symbol')}",
                metadata={
                    "execution_impact_bps": impact,
                    "fill_ratio": completion,
                    "book_age_ms": 0.0,
                    "in_expectancy": float(row.get("in_expectancy", 0.0)),
                    "out_expectancy": out_expectancy,
                },
            ))
        return opportunities

    def run(
        self,
        *,
        available_capital: float = 1000.0,
        current_exposure: float = 0.0,
        max_exposure: float = 350.0,
        kill_switch: bool = False,
    ) -> list[dict]:
        validation = self._read_json(self.validation_path)
        replay = self._read_json(self.replay_path)
        if not validation or not replay or not isinstance(replay.get("trades"), list):
            return []

        engine = GodUltraEngine()
        risk = RiskSnapshot(
            available_capital=float(available_capital),
            current_exposure=float(current_exposure),
            max_exposure=float(max_exposure),
            kill_switch=bool(kill_switch),
        )
        intents = engine.select(self.build_opportunities(), risk)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        rows = []
        for intent in intents:
            row = asdict(intent)
            row["paper"] = True
            row["created_at"] = now
            row["intent_id"] = uuid.uuid4().hex
            rows.append(row)
            with self.output_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
        return rows
