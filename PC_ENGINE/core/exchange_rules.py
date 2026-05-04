from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict


@dataclass
class SymbolRules:
    symbol: str
    min_qty: float = 0.0
    step_size: float = 0.0
    tick_size: float = 0.0
    min_notional: float = 0.0
    amount_precision: int | None = None
    price_precision: int | None = None


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def floor_to_step(value: float, step: float) -> float:
    if step <= 0:
        return value
    d_value = Decimal(str(value))
    d_step = Decimal(str(step))
    return float((d_value / d_step).to_integral_value(rounding=ROUND_DOWN) * d_step)


class ExchangeRulesEngine:
    def __init__(self):
        self.cache: Dict[str, SymbolRules] = {}

    def load_symbol_rules(self, exchange_client, symbol: str) -> SymbolRules:
        cache_key = f"{exchange_client.name}:{symbol}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        market = {}
        client = getattr(exchange_client, "client", None)
        try:
            if client:
                if not getattr(client, "markets", None):
                    client.load_markets()
                market = client.market(symbol)
        except Exception:
            market = {}

        limits = market.get("limits", {}) if isinstance(market, dict) else {}
        precision = market.get("precision", {}) if isinstance(market, dict) else {}
        info = market.get("info", {}) if isinstance(market, dict) else {}

        min_qty = _float(limits.get("amount", {}).get("min"))
        min_notional = _float(limits.get("cost", {}).get("min"))
        step_size = 0.0
        tick_size = 0.0

        for item in info.get("filters", []) if isinstance(info, dict) else []:
            if item.get("filterType") in {"LOT_SIZE", "MARKET_LOT_SIZE"}:
                step_size = step_size or _float(item.get("stepSize"))
                min_qty = min_qty or _float(item.get("minQty"))
            if item.get("filterType") == "PRICE_FILTER":
                tick_size = tick_size or _float(item.get("tickSize"))
            if item.get("filterType") in {"MIN_NOTIONAL", "NOTIONAL"}:
                min_notional = min_notional or _float(item.get("minNotional"))

        rules = SymbolRules(
            symbol=symbol,
            min_qty=min_qty,
            step_size=step_size,
            tick_size=tick_size,
            min_notional=min_notional,
            amount_precision=precision.get("amount") if isinstance(precision, dict) else None,
            price_precision=precision.get("price") if isinstance(precision, dict) else None,
        )
        self.cache[cache_key] = rules
        return rules

    def normalize_qty(self, exchange_client, symbol: str, qty: float) -> float:
        rules = self.load_symbol_rules(exchange_client, symbol)
        qty = floor_to_step(qty, rules.step_size)
        if rules.amount_precision is not None and rules.amount_precision >= 0:
            qty = round(qty, int(rules.amount_precision))
        return max(0.0, qty)

    def validate_order(self, exchange_client, symbol: str, qty: float, price: float) -> tuple[bool, str, float]:
        rules = self.load_symbol_rules(exchange_client, symbol)
        normalized_qty = self.normalize_qty(exchange_client, symbol, qty)
        if normalized_qty <= 0:
            return False, "qty normalized to zero", normalized_qty
        if rules.min_qty and normalized_qty < rules.min_qty:
            return False, f"qty below min_qty {rules.min_qty}", normalized_qty
        notional = normalized_qty * price
        if rules.min_notional and notional < rules.min_notional:
            return False, f"notional below min_notional {rules.min_notional}", normalized_qty
        return True, "ok", normalized_qty
