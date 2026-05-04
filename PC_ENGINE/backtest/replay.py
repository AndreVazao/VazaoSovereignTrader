from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from PC_ENGINE.core.strategy import TrendEmaAtrStrategy


@dataclass
class BacktestResult:
    symbol: str
    trades: int
    wins: int
    losses: int
    pnl_pct: float
    max_drawdown_pct: float
    profit_factor: float


class ReplayBacktester:
    def __init__(self, strategy: TrendEmaAtrStrategy, fee_pct: float = 0.001, slippage_pct: float = 0.0005):
        self.strategy = strategy
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct

    def run(self, symbol: str, candles: List[List[float]]) -> BacktestResult:
        position_entry = 0.0
        trades = wins = losses = 0
        pnl = 0.0
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        gross_profit = 0.0
        gross_loss = 0.0

        for i in range(60, len(candles)):
            window = candles[:i]
            price = float(window[-1][4])
            signal = self.strategy.analyse(symbol, window, spread_pct=0.0005)
            if position_entry <= 0 and signal.action == "BUY":
                position_entry = price * (1 + self.slippage_pct)
            elif position_entry > 0 and signal.action == "SELL":
                exit_price = price * (1 - self.slippage_pct)
                trade_pnl = (exit_price - position_entry) / position_entry - (self.fee_pct * 2)
                trades += 1
                pnl += trade_pnl
                equity += trade_pnl
                if trade_pnl >= 0:
                    wins += 1
                    gross_profit += trade_pnl
                else:
                    losses += 1
                    gross_loss += abs(trade_pnl)
                peak = max(peak, equity)
                max_dd = min(max_dd, equity - peak)
                position_entry = 0.0

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        return BacktestResult(symbol, trades, wins, losses, pnl, max_dd, profit_factor)
