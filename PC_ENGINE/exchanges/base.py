from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ExchangeClient(ABC):
    name: str

    @abstractmethod
    def fetch_balance(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def free_quote_balance(self, quote: str = "USDT") -> float:
        raise NotImplementedError

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> List[List[float]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_spread_pct(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def market_buy(self, symbol: str, qty: float) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def market_sell(self, symbol: str, qty: float) -> Dict[str, Any]:
        raise NotImplementedError

    def fetch_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        """Return currently open exchange orders; fail closed if unsupported."""
        raise NotImplementedError("open-order reconciliation is not supported")

    def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Return exchange order state; implementations must fail closed if unsupported."""
        raise NotImplementedError("exchange order reconciliation is not supported")
