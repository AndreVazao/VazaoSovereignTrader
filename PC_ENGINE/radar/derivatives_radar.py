from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any


@dataclass(frozen=True)
class DerivativeSnapshot:
    exchange: str
    symbol: str
    funding_rate: float | None
    open_interest: float | None
    open_interest_value: float | None
    mark_price: float | None
    index_price: float | None
    basis_bps: float | None
    timestamp_ms: int
    source: str = "public"


@dataclass(frozen=True)
class DerivativeEvidence:
    score: float
    confidence: float
    snapshots: int
    rationale: tuple[str, ...]
    paper_only: bool = True


class DerivativesRadar:
    """Public derivatives context collector. Observation-only; never places orders."""

    def __init__(self, exchanges: list[str] | None = None, data_dir: str | Path = "PC_ENGINE/data/radar",
                 cache_seconds: float = 10.0, funding_scale: float = 0.0005) -> None:
        self.exchanges = tuple(dict.fromkeys((exchanges or ["binance", "bingx", "okx", "bybit"])))
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_seconds = max(1.0, float(cache_seconds))
        self.funding_scale = max(1e-9, float(funding_scale))
        self._cache: dict[str, tuple[float, list[DerivativeSnapshot]]] = {}
        self._previous_oi: dict[tuple[str, str], float] = {}
        self._previous_price: dict[str, float] = {}

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _basis_bps(cls, mark: Any, index: Any) -> float | None:
        mark_f = cls._safe_float(mark)
        index_f = cls._safe_float(index)
        if mark_f is None or index_f in (None, 0):
            return None
        return (mark_f / index_f - 1.0) * 10_000.0

    def collect(self, symbol: str, force: bool = False) -> list[DerivativeSnapshot]:
        now = time.monotonic()
        cached = self._cache.get(symbol)
        if cached and not force and now - cached[0] < self.cache_seconds:
            return cached[1]
        snapshots: list[DerivativeSnapshot] = []
        try:
            import ccxt
        except ImportError:
            self._cache[symbol] = (now, snapshots)
            return snapshots

        for exchange_name in self.exchanges:
            try:
                exchange_cls = getattr(ccxt, exchange_name)
                exchange = exchange_cls({"enableRateLimit": True, "options": {"defaultType": "swap"}})
                if not exchange.has.get("fetchFundingRate") and not exchange.has.get("fetchOpenInterest"):
                    continue
                funding = exchange.fetch_funding_rate(symbol) if exchange.has.get("fetchFundingRate") else {}
                oi = exchange.fetch_open_interest(symbol) if exchange.has.get("fetchOpenInterest") else {}
                ticker = exchange.fetch_ticker(symbol) if exchange.has.get("fetchTicker") else {}
                info = funding.get("info", {}) if isinstance(funding, dict) else {}
                oi_info = oi.get("info", {}) if isinstance(oi, dict) else {}
                ticker_info = ticker.get("info", {}) if isinstance(ticker, dict) else {}
                funding_rate = self._safe_float(funding.get("fundingRate") if isinstance(funding, dict) else None)
                open_interest = self._safe_float(oi.get("openInterestValue") if isinstance(oi, dict) else None)
                if open_interest is None:
                    open_interest = self._safe_float(oi.get("openInterestAmount") if isinstance(oi, dict) else None)
                mark = self._safe_float((ticker.get("markPrice") if isinstance(ticker, dict) else None) or info.get("markPrice") or ticker_info.get("markPrice"))
                index = self._safe_float((ticker.get("indexPrice") if isinstance(ticker, dict) else None) or info.get("indexPrice") or ticker_info.get("indexPrice"))
                ts = int((funding.get("timestamp") if isinstance(funding, dict) else None) or (oi.get("timestamp") if isinstance(oi, dict) else None) or int(time.time() * 1000))
                snapshots.append(DerivativeSnapshot(exchange_name, symbol, funding_rate, open_interest, None, mark, index, self._basis_bps(mark, index), ts))
            except Exception:
                continue
        self._cache[symbol] = (now, snapshots)
        self._persist(symbol, snapshots)
        return snapshots

    def evidence(self, symbol: str, price: float, snapshots: list[DerivativeSnapshot] | None = None) -> DerivativeEvidence:
        snapshots = snapshots if snapshots is not None else self.collect(symbol)
        if not snapshots:
            return DerivativeEvidence(0.0, 0.0, 0, ("sem dados de derivados públicos",))
        scores: list[float] = []
        rationale: list[str] = []
        price_change = None
        previous_price = self._previous_price.get(symbol)
        if previous_price and previous_price > 0:
            price_change = price / previous_price - 1.0
        self._previous_price[symbol] = price
        for snap in snapshots:
            local: list[float] = []
            if snap.funding_rate is not None:
                # Positive funding implies long-side crowding; negative implies short-side crowding.
                local.append(max(-1.0, min(1.0, -snap.funding_rate / self.funding_scale)))
                rationale.append(f"{snap.exchange}: funding={snap.funding_rate:.6g}")
            key = (snap.exchange, symbol)
            previous_oi = self._previous_oi.get(key)
            if snap.open_interest is not None and previous_oi and previous_oi > 0 and price_change is not None:
                oi_change = snap.open_interest / previous_oi - 1.0
                if abs(oi_change) >= 0.001 and abs(price_change) >= 0.001:
                    local.append(max(-1.0, min(1.0, (1 if price_change > 0 else -1) * (1 if oi_change > 0 else -1))))
                    rationale.append(f"{snap.exchange}: preço/OI {'alinhados' if price_change * oi_change > 0 else 'divergentes'}")
            if snap.basis_bps is not None:
                local.append(max(-1.0, min(1.0, -snap.basis_bps / 20.0)))
            if snap.open_interest is not None:
                self._previous_oi[key] = snap.open_interest
            if local:
                scores.append(sum(local) / len(local))
        score = sum(scores) / len(scores) if scores else 0.0
        confidence = min(1.0, len(scores) / max(2, len(snapshots))) * min(1.0, 0.5 + abs(score) * 0.5)
        return DerivativeEvidence(round(max(-1.0, min(1.0, score)), 4), round(confidence, 4), len(snapshots), tuple(rationale))

    def _persist(self, symbol: str, snapshots: list[DerivativeSnapshot]) -> None:
        path = self.data_dir / "derivatives_events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            for snapshot in snapshots:
                handle.write(json.dumps(asdict(snapshot), ensure_ascii=False) + "\n")
