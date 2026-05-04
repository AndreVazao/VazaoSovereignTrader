from __future__ import annotations

from dataclasses import dataclass

from PC_ENGINE.core.exchange_rules import ExchangeRulesEngine
from PC_ENGINE.core.paper_broker import PaperBroker


@dataclass
class OrderResult:
    ok: bool
    side: str
    symbol: str
    qty: float
    price: float
    fee: float
    order_id: str
    reason: str


class OrderManager:
    def __init__(self, rules: ExchangeRulesEngine, paper_broker: PaperBroker):
        self.rules = rules
        self.paper_broker = paper_broker
        self.last_client_order: set[str] = set()

    def buy(self, exchange, symbol: str, qty: float, price: float, paper: bool, spread_pct: float = 0.0) -> OrderResult:
        return self._execute(exchange, symbol, "buy", qty, price, paper, spread_pct)

    def sell(self, exchange, symbol: str, qty: float, price: float, paper: bool, spread_pct: float = 0.0) -> OrderResult:
        return self._execute(exchange, symbol, "sell", qty, price, paper, spread_pct)

    def _execute(self, exchange, symbol: str, side: str, qty: float, price: float, paper: bool, spread_pct: float) -> OrderResult:
        valid, reason, normalized_qty = self.rules.validate_order(exchange, symbol, qty, price)
        if not valid:
            return OrderResult(False, side, symbol, normalized_qty, price, 0.0, "", reason)

        fingerprint = f"{exchange.name}:{symbol}:{side}:{round(normalized_qty, 12)}"
        if fingerprint in self.last_client_order:
            return OrderResult(False, side, symbol, normalized_qty, price, 0.0, "", "duplicate blocked")
        self.last_client_order.add(fingerprint)
        if len(self.last_client_order) > 500:
            self.last_client_order.clear()

        if paper:
            fill = self.paper_broker.fill(symbol, side, normalized_qty, price, spread_pct)
            return OrderResult(True, side, symbol, normalized_qty, fill.fill_price, fill.fee, f"paper-{side}", "paper fill")

        try:
            if side == "buy":
                raw = exchange.market_buy(symbol, normalized_qty)
            else:
                raw = exchange.market_sell(symbol, normalized_qty)
            return OrderResult(True, side, symbol, normalized_qty, price, 0.0, str(raw.get("id", "")), "exchange accepted")
        except Exception as exc:
            return OrderResult(False, side, symbol, normalized_qty, price, 0.0, "", f"exchange error: {exc}")
