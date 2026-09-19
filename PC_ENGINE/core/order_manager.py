from __future__ import annotations

import time
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
    def __init__(self, rules: ExchangeRulesEngine, paper_broker: PaperBroker, duplicate_window_seconds: float = 5.0):
        self.rules = rules
        self.paper_broker = paper_broker
        self.duplicate_window_seconds = float(duplicate_window_seconds)
        self.last_client_order: dict[str, float] = {}

    def buy(self, exchange, symbol: str, qty: float, price: float, paper: bool, spread_pct: float = 0.0) -> OrderResult:
        return self._execute(exchange, symbol, "buy", qty, price, paper, spread_pct)

    def sell(self, exchange, symbol: str, qty: float, price: float, paper: bool, spread_pct: float = 0.0) -> OrderResult:
        return self._execute(exchange, symbol, "sell", qty, price, paper, spread_pct)

    def _execute(self, exchange, symbol: str, side: str, qty: float, price: float, paper: bool, spread_pct: float) -> OrderResult:
        valid, reason, normalized_qty = self.rules.validate_order(exchange, symbol, qty, price)
        if not valid:
            return OrderResult(False, side, symbol, normalized_qty, price, 0.0, "", reason)

        fingerprint = f"{exchange.name}:{symbol}:{side}:{round(normalized_qty, 12)}:{round(price, 8)}"
        now = time.monotonic()
        last = self.last_client_order.get(fingerprint)
        if last is not None and now - last < self.duplicate_window_seconds:
            return OrderResult(False, side, symbol, normalized_qty, price, 0.0, "", "duplicate blocked")
        self.last_client_order[fingerprint] = now

        try:
            if paper:
                fill = self.paper_broker.fill(symbol, side, normalized_qty, price, spread_pct)
                return OrderResult(True, side, symbol, normalized_qty, fill.fill_price, fill.fee, f"paper-{side}", "paper fill")

            raw = exchange.market_buy(symbol, normalized_qty) if side == "buy" else exchange.market_sell(symbol, normalized_qty)
            filled_qty = float(raw.get("filled") or raw.get("amount") or normalized_qty)
            fill_price = float(raw.get("average") or raw.get("price") or price)
            fee = self._extract_fee(raw, symbol, fill_price)
            return OrderResult(True, side, symbol, filled_qty, fill_price, fee, str(raw.get("id", "")), "exchange accepted")
        except Exception as exc:
            self.last_client_order.pop(fingerprint, None)
            return OrderResult(False, side, symbol, normalized_qty, price, 0.0, "", f"exchange error: {exc}")

    @staticmethod
    def _extract_fee(raw: dict, symbol: str, fill_price: float) -> float:
        base, quote = symbol.split("/", 1)
        items = []
        fee = raw.get("fee")
        if isinstance(fee, dict):
            items.append(fee)
        fees = raw.get("fees")
        if isinstance(fees, list):
            items.extend(item for item in fees if isinstance(item, dict))
        total = 0.0
        for item in items:
            cost = float(item.get("cost") or 0.0)
            currency = str(item.get("currency") or "")
            if currency == base:
                cost *= fill_price
            elif currency and currency != quote:
                continue
            total += cost
        return total
