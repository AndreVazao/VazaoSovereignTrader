from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class StrategyScore:
    name: str
    trades: int = 0
    pnl_pct: float = 0.0
    max_drawdown_pct: float = 0.0

    @property
    def score(self) -> float:
        dd_penalty = abs(self.max_drawdown_pct) * 2
        activity_penalty = 0.01 if self.trades == 0 else 0.0
        return self.pnl_pct - dd_penalty - activity_penalty


class ChampionChallenger:
    def __init__(self, champion_name: str = "trend_ema_atr"):
        self.champion = StrategyScore(champion_name)
        self.challengers: Dict[str, StrategyScore] = {}

    def record(self, name: str, pnl_pct: float, drawdown_pct: float = 0.0, live: bool = False) -> None:
        target = self.champion if live or name == self.champion.name else self.challengers.setdefault(name, StrategyScore(name))
        target.trades += 1
        target.pnl_pct += pnl_pct
        target.max_drawdown_pct = min(target.max_drawdown_pct, drawdown_pct)

    def recommendation(self) -> dict:
        if not self.challengers:
            return {"action": "keep", "reason": "no challenger data"}
        best = max(self.challengers.values(), key=lambda item: item.score)
        if best.trades >= 30 and best.score > self.champion.score * 1.2:
            return {"action": "review_challenger", "candidate": best.name, "reason": "challenger outperforming in paper"}
        return {"action": "keep", "reason": "champion remains preferred"}
