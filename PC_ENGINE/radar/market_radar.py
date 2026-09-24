from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import ccxt


@dataclass(frozen=True)
class VenueSnapshot:
    exchange: str
    symbol: str
    price: float
    bid: float
    ask: float
    volume: float
    exchange_ts_ms: int | None
    local_ts_ms: int
    latency_ms: int | None


@dataclass(frozen=True)
class LeadLagObservation:
    symbol: str
    leader: str
    follower: str
    leader_return_pct: float
    follower_return_pct: float
    leader_local_ts_ms: int
    follower_local_ts_ms: int
    lag_ms: int
    direction: str


class MarketRadar:
    """Observational cross-exchange radar.

    Never places orders. It collects public ticker snapshots, measures
    cross-venue dispersion and records candidate lead/lag events. The first
    version uses CCXT polling; WebSocket adapters can be added later after
    empirical validation of the data model.
    """

    def __init__(self, exchanges: list[str], symbols: list[str], data_dir: str | Path = "PC_ENGINE/data/radar"):
        self.exchanges = list(dict.fromkeys(exchanges))
        self.symbols = list(dict.fromkeys(symbols))
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.clients: dict[str, Any] = {}
        self.previous: dict[tuple[str, str], VenueSnapshot] = {}
        self.last_pressure: dict[str, float] = {}
        self.quality_rejections = 0
        self._build_clients()

    def _build_clients(self) -> None:
        for name in self.exchanges:
            try:
                exchange_cls = getattr(ccxt, name)
                self.clients[name] = exchange_cls({"enableRateLimit": True})
                try:
                    self.clients[name].load_markets()
                except Exception:
                    pass
            except Exception:
                continue

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
            return number if math.isfinite(number) else default
        except (TypeError, ValueError):
            return default

    @classmethod
    def _validate_ticker_snapshot(
        cls,
        *,
        price: Any,
        bid: Any,
        ask: Any,
        volume: Any,
        exchange_ts_ms: Any,
    ) -> bool:
        """Fail closed on malformed venue observations before radar evidence is used."""
        try:
            values = [float(price), float(bid), float(ask), float(volume)]
        except (TypeError, ValueError):
            return False
        if not all(math.isfinite(value) for value in values):
            return False
        if values[0] <= 0 or values[3] < 0:
            return False
        bid_value, ask_value = values[1], values[2]
        if bid_value < 0 or ask_value < 0:
            return False
        if bid_value > 0 and ask_value > 0 and ask_value < bid_value:
            return False
        if exchange_ts_ms is not None:
            try:
                timestamp = float(exchange_ts_ms)
            except (TypeError, ValueError):
                return False
            if not math.isfinite(timestamp) or timestamp <= 0:
                return False
        return True

    def snapshot(self) -> tuple[list[VenueSnapshot], list[LeadLagObservation]]:
        snapshots: list[VenueSnapshot] = []
        for exchange_name, client in self.clients.items():
            for symbol in self.symbols:
                request_start_ms = int(time.time() * 1000)
                try:
                    ticker = client.fetch_ticker(symbol)
                    local_ts_ms = int(time.time() * 1000)
                    price = self._safe_float(ticker.get("last"))
                    bid = self._safe_float(ticker.get("bid"))
                    ask = self._safe_float(ticker.get("ask"))
                    volume = self._safe_float(ticker.get("baseVolume"))
                    if price <= 0:
                        continue
                    exchange_ts = ticker.get("timestamp")
                    exchange_ts_ms = int(exchange_ts) if exchange_ts is not None else None
                    if not self._validate_ticker_snapshot(
                        price=price,
                        bid=bid,
                        ask=ask,
                        volume=volume,
                        exchange_ts_ms=exchange_ts_ms,
                    ):
                        self.quality_rejections += 1
                        continue
                    latency = local_ts_ms - exchange_ts_ms if exchange_ts_ms is not None else local_ts_ms - request_start_ms
                    snapshots.append(VenueSnapshot(exchange_name, symbol, price, bid, ask, volume, exchange_ts_ms, local_ts_ms, latency))
                except Exception:
                    continue

        self.last_pressure = self._pressure_from_previous(snapshots)
        leads = self._detect_leads(snapshots)
        self._persist(snapshots, leads)
        for snap in snapshots:
            self.previous[(snap.exchange, snap.symbol)] = snap
        return snapshots, leads

    def _pressure_from_previous(self, snapshots: list[VenueSnapshot]) -> dict[str, float]:
        grouped: dict[str, list[float]] = {}
        for snap in snapshots:
            prev = self.previous.get((snap.exchange, snap.symbol))
            if prev and prev.price > 0:
                grouped.setdefault(snap.symbol, []).append((snap.price - prev.price) / prev.price)
        return {
            symbol: round(max(-1.0, min(1.0, sum(values) / max(1, len(values)) / 0.002)), 4)
            for symbol, values in grouped.items()
        }

    def _detect_leads(self, current: list[VenueSnapshot]) -> list[LeadLagObservation]:
        by_symbol: dict[str, list[VenueSnapshot]] = {}
        for snap in current:
            by_symbol.setdefault(snap.symbol, []).append(snap)

        observations: list[LeadLagObservation] = []
        min_move_pct = 0.0005
        for symbol, snaps in by_symbol.items():
            movers: list[tuple[VenueSnapshot, float]] = []
            for snap in snaps:
                prev = self.previous.get((snap.exchange, symbol))
                if not prev or prev.price <= 0:
                    continue
                ret = (snap.price - prev.price) / prev.price
                if abs(ret) >= min_move_pct:
                    movers.append((snap, ret))
            movers.sort(key=lambda item: item[0].local_ts_ms)
            for index, (leader, leader_ret) in enumerate(movers):
                for follower, follower_ret in movers[index + 1 :]:
                    if leader.exchange == follower.exchange or leader_ret * follower_ret <= 0:
                        continue
                    lag = follower.local_ts_ms - leader.local_ts_ms
                    if lag < 0:
                        continue
                    observations.append(
                        LeadLagObservation(
                            symbol=symbol,
                            leader=leader.exchange,
                            follower=follower.exchange,
                            leader_return_pct=round(leader_ret * 100, 6),
                            follower_return_pct=round(follower_ret * 100, 6),
                            leader_local_ts_ms=leader.local_ts_ms,
                            follower_local_ts_ms=follower.local_ts_ms,
                            lag_ms=lag,
                            direction="UP" if leader_ret > 0 else "DOWN",
                        )
                    )
        return observations

    def pressure(self, snapshots: list[VenueSnapshot] | None = None) -> dict[str, float]:
        """Return the latest descriptive pressure score, never an order signal."""
        if snapshots is None:
            return dict(self.last_pressure)
        return self._pressure_from_previous(snapshots)

    def _persist(self, snapshots: list[VenueSnapshot], leads: list[LeadLagObservation]) -> None:
        path = self.data_dir / "observations.jsonl"
        row = {
            "local_ts_ms": int(time.time() * 1000),
            "snapshots": [asdict(x) for x in snapshots],
            "lead_lag": [asdict(x) for x in leads],
            "pressure": dict(self.last_pressure),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def close(self) -> None:
        for client in self.clients.values():
            try:
                client.close()
            except Exception:
                pass
