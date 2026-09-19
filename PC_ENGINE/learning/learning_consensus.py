from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

from PC_ENGINE.learning.state_signature import SignatureStat


@dataclass(frozen=True)
class LearningConsensus:
    signature_confirmed: bool
    outcome_confirmed: bool
    agreement: bool
    bonus: float
    reason: str


class PaperLearningConsensus:
    """Cross-check signature learning against independent state outcomes.

    PAPER-only evidence. This component never authorizes an order, changes risk,
    or switches REAL mode.
    """

    def __init__(self, settings: dict | None = None) -> None:
        settings = settings or {}
        data_dir = Path(settings.get("data_dir", "PC_ENGINE/data/radar"))
        self.learning_path = Path(settings.get("learning_path", str(data_dir / "state_signature_learning.jsonl")))
        self.outcome_path = Path(settings.get("outcome_path", str(data_dir / "state_outcomes.jsonl")))
        self.horizon_ms = max(1000, int(settings.get("horizon_ms", 5000)))
        self.max_bonus = max(0.0, min(0.10, float(settings.get("consensus_max_bonus", settings.get("max_bonus", 0.06)))))
        self.min_outcome_samples = max(1, int(settings.get("consensus_min_outcome_samples", settings.get("min_outcome_samples", 30))))
        self._learning_mtime = -1.0
        self._outcome_mtime = -1.0
        self._learning: list[SignatureStat] = []
        self._outcomes: list[dict] = []

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        if not path.exists():
            return []
        rows: list[dict] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        except OSError:
            return []
        return rows

    def _load(self) -> None:
        try:
            mtime = self.learning_path.stat().st_mtime
        except FileNotFoundError:
            mtime = -1.0
        if mtime != self._learning_mtime:
            rows = self._read_jsonl(self.learning_path)
            self._learning = []
            for row in rows:
                try:
                    self._learning.append(SignatureStat(**row))
                except (TypeError, ValueError):
                    continue
            self._learning_mtime = mtime

        try:
            mtime = self.outcome_path.stat().st_mtime
        except FileNotFoundError:
            mtime = -1.0
        if mtime != self._outcome_mtime:
            self._outcomes = self._read_jsonl(self.outcome_path)
            self._outcome_mtime = mtime

    def evaluate(self, state: dict) -> LearningConsensus:
        self._load()
        if str(state.get("action", "HOLD")) != "BUY":
            return LearningConsensus(False, False, False, 0.0, "consenso apenas para BUY")

        symbol = str(state.get("symbol", ""))
        regime = str(state.get("regime", "UNKNOWN"))
        signature = None
        for row in self._learning:
            if row.horizon_ms == self.horizon_ms and row.eligible:
                # Reuse the same hierarchical ranking semantics as the learner.
                from PC_ENGINE.learning.state_signature import StateSignature
                if row.signature in StateSignature.hierarchy(state):
                    if signature is None or (row.samples, row.lower_ci_bps) > (signature.samples, signature.lower_ci_bps):
                        signature = row

        signature_confirmed = signature is not None
        matching = [
            row for row in self._outcomes
            if str(row.get("symbol", "")) == symbol
            and str(row.get("action", "")) == "BUY"
            and str(row.get("regime", "")) == regime
            and int(row.get("horizon_ms", 0) or 0) == self.horizon_ms
            and bool(row.get("eligible"))
            and int(row.get("samples", 0) or 0) >= self.min_outcome_samples
        ]
        outcome_confirmed = bool(matching)
        if signature_confirmed and outcome_confirmed:
            strength = max(0.0, min(1.0, float(matching[0].get("lower_ci_bps", 0.0)) / 100.0))
            bonus = min(self.max_bonus, self.max_bonus * strength)
            return LearningConsensus(True, True, True, bonus, "assinatura e outcome independente confirmam BUY")
        if signature_confirmed:
            return LearningConsensus(True, False, False, 0.0, "assinatura elegível sem confirmação agregada")
        if outcome_confirmed:
            return LearningConsensus(False, True, False, 0.0, "outcome agregado elegível sem assinatura confirmada")
        return LearningConsensus(False, False, False, 0.0, "sem consenso histórico elegível")
