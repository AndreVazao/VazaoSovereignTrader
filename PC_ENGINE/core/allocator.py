from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AllocationDecision:
    symbol: str
    score: float
    allocation_pct: float
    max_notional: float
    reason: str


class CapitalAllocator:
    def __init__(self, engine_settings: dict, symbol_limits: dict):
        self.engine_settings = engine_settings
        self.symbol_limits = symbol_limits

    def allocate(self, equity: float, scores: dict[str, float]) -> list[AllocationDecision]:
        if equity <= 0:
            return []
        positive = {symbol: max(0.0, score) for symbol, score in scores.items() if score > 0}
        if not positive:
            return []
        total_score = sum(positive.values())
        if total_score <= 0:
            return []

        max_total = equity * float(self.engine_settings["max_total_exposure_pct"])
        decisions: list[AllocationDecision] = []
        for symbol, score in sorted(positive.items(), key=lambda item: item[1], reverse=True):
            raw_pct = score / total_score
            symbol_cap_pct = float(self.symbol_limits.get(symbol, {}).get("max_exposure_pct", 0.10))
            allocation_pct = min(raw_pct * float(self.engine_settings["max_total_exposure_pct"]), symbol_cap_pct)
            max_notional = min(equity * allocation_pct, max_total)
            decisions.append(
                AllocationDecision(
                    symbol=symbol,
                    score=round(score, 4),
                    allocation_pct=round(allocation_pct, 4),
                    max_notional=round(max_notional, 8),
                    reason="score weighted allocation with per-symbol cap",
                )
            )
        return decisions[: int(self.engine_settings["max_open_positions"])]
