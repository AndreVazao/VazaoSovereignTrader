from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Literal, Optional

BotMode = Literal["PAPER", "REAL"]
BotStatus = Literal["OFF", "RUNNING", "PAUSED", "SAFE_MODE", "KILL_SWITCH"]
SignalAction = Literal["BUY", "SELL", "HOLD"]
Regime = Literal["TREND_UP", "TREND_DOWN", "RANGE", "CHAOS", "WARMUP"]


@dataclass
class AssetSnapshot:
    symbol: str
    price: float
    score: float
    regime: Regime
    allocation_pct: float
    in_position: bool


@dataclass
class BotSnapshot:
    status: BotStatus
    mode: BotMode
    balance: float
    equity: float
    pnl_today_pct: float
    pnl_week_pct: float
    drawdown_pct: float
    open_positions: int
    assets: List[AssetSnapshot]
    logs: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TradeRecord:
    ts: int
    exchange: str
    symbol: str
    side: str
    qty: float
    price: float
    fee: float
    pnl_pct: float
    reason: str
