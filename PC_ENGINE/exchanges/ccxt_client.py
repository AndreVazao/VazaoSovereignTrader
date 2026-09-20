from __future__ import annotations

import os
from typing import Any, Dict, List

import ccxt

from .base import ExchangeClient


class CcxtExchangeClient(ExchangeClient):
    def __init__(self, name: str, key_env: str, private_env: str, paper: bool = True):
        self.name = name
        self.paper = paper
        exchange_cls = getattr(ccxt, name)
        key = os.getenv(key_env, "")
        private = os.getenv(private_env, "")
        params: Dict[str, Any] = {"enableRateLimit": True}
        if key and private:
            params.update({"apiKey": key, "secret": private})
        self.client = exchange_cls(params)
        try:
            self.client.load_markets()
        except Exception:
            pass

    def fetch_balance(self) -> Dict[str, Any]:
        if self.paper:
            return {"free": {"USDT": 1000.0}, "total": {"USDT": 1000.0}}
        return self.client.fetch_balance()

    def free_quote_balance(self, quote: str = "USDT") -> float:
        balance = self.fetch_balance()
        free = balance.get("free", {})
        return float(free.get(quote, 0.0))

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        return self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return self.client.fetch_ticker(symbol)

    def fetch_spread_pct(self, symbol: str) -> float:
        book = self.client.fetch_order_book(symbol, limit=5)
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        if not bids or not asks:
            return 1.0
        bid = float(bids[0][0])
        ask = float(asks[0][0])
        if bid <= 0:
            return 1.0
        return (ask - bid) / bid

    def market_buy(self, symbol: str, qty: float) -> Dict[str, Any]:
        if self.paper:
            return {"id": "paper-buy", "symbol": symbol, "side": "buy", "amount": qty}
        amount = float(self.client.amount_to_precision(symbol, qty))
        return self.client.create_market_buy_order(symbol, amount)

    def market_sell(self, symbol: str, qty: float) -> Dict[str, Any]:
        if self.paper:
            return {"id": "paper-sell", "symbol": symbol, "side": "sell", "amount": qty}
        amount = float(self.client.amount_to_precision(symbol, qty))
        return self.client.create_market_sell_order(symbol, amount)

    def fetch_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        if self.paper:
            return []
        return self.client.fetch_open_orders(symbol) if symbol else self.client.fetch_open_orders()

    def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        if self.paper:
            return {"id": order_id, "symbol": symbol, "status": "closed", "filled": 0.0}
        return self.client.fetch_order(order_id, symbol)
