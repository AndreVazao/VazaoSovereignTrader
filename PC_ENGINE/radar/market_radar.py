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

    This module never places orders. It collects public ticker snapshots,
    measures cross-venue dispersion and records candidate lead/lag events.
    The first version intentionally uses CCXT polling so it has no additional
    runtime dependency. WebSocket adapters can be added later after the data
    model and empirical tests prove useful.
    """

    def __init__(self, exchanges: list[str], symbols: list[str], data_dir: str | Path = "PC_ENGINE/data/radar"):
        self.exchanges = list(dict.fromkeys(exchanges))
        self.symbols = list(dict.fromkeys(symbols))
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.clients: dict[str, Any] = {}
        self.previous: dict[tuple[str, str], VenueSnapshot] = {}
        self._build_clients()

    def _build_clients(self) -> None:
        for name in self.exchanges:
            exchange_cls = getattr(ccxt, name)
            self.clients[name] = exchange_cls({"enableRateLimit": True})
            try:
                self.clients[name].load_markets()
            except Exception:
                # A venue may be temporarily unavailable. It remains visible
                # in the radar and can recover on a later poll.
                continue

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
            return number if math.isfinite(number) else default
        except (TypeError, ValueError):
            return default

    def snapshot(self) -> tuple[list[VenueSnapshot], list[LeadLagObservation]]:
        now_ms = int(time.time() * 1000)
        snapshots: list[VenueSnapshot] = []
        for exchange_name, client in self.clients.items():
            for symbol in self.symbols:
                try:
                    ticker = client.fetch_ticker(symbol)
                    price = self._safe_float(ticker.get("last"))
                    bid = self._safe_float(ticker.get("bid"))
                    ask = self._safe_float(ticker.get("ask"))
                    volume = self._safe_float(ticker.get("baseVolume"))
                    if price <= 0:
                        continue
                    exchange_ts = ticker.get("timestamp")
                    exchange_ts_ms = int(exchange_ts) if exchange_ts is not None else None
                    latency = now_ms - exchange_ts_ms if exchange_ts_ms is not None else None
                    snap = VenueSnapshot(exchange_name, symbol, price, bid, ask, volume, exchange_ts_ms, now_ms, latency)
                    snapshots.append(snap)
                except Exception:
                    continue

        leads = self._detect_leads(snapshots)
        for snap in snapshots:
            self.previous[(snap.exchange, snap.symbol)] = snap
        self._persist(snapshots, leads)
        return snapshots, leads

    def _detect_leads(self, current: list[VenueSnapshot]) -> list[LeadLagObservation]:
        by_symbol: dict[str, list[VenueSnapshot]] = {}
        for snap in current:
            by_symbol.setdefault(snap.symbol, []).append(snap)

        observations: list[LeadLagObservation] = []
        min_move_pct = 0.0005  # 5 bps; deliberately conservative for first collection phase.
        for symbol, snaps in by_symbol.items():
            movers: list[tuple[VenueSnapshot, float]] = []
            for snap in snaps:
                prev = self.previous.get((snap.exchange, symbol))
                if not prev or prev.price <= 0:
                    continue
                ret = (snap.price - prev.price) / prev.price
                if abs(ret) >= min_move_pct:
                    movers.append((snap, ret))
            movers.sort(key=lambda item: abs(item[1]), reverse=True)
            if len(movers) < 2:
                continue
            leader, leader_ret = movers[0]
            for follower, follower_ret in movers[1:]:
                if leader.exchange == follower.exchange:
                    continue
                same_direction = leader_ret * follower_ret > 0
                if not same_direction:
                    continue
                lag = max(0, follower.local_ts_ms - leader.local_ts_ms)
                direction = "UP" if leader_ret > 0 else "DOWN"
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
                        direction=direction,
                    )
                )
        return observations

    def pressure(self, snapshots: list[VenueSnapshot]) -> dict[str, float]:
        """Return a simple cross-venue pressure score, not a trading signal."""
        grouped: dict[str, list[float]] = {}
        for snap in snapshots:
            prev = self.previous.get((snap.exchange, snap.symbol))
            if prev and prev.price > 0:
                grouped.setdefault(snap.symbol, []).append((snap.price - prev.price) / prev.price)
        return {
            symbol: round(max(-1.0, min(1.0, sum(values) / max(1, len(values)) / 0.002)), 4)
            for symbol, values in grouped.items()
        }

    def _persist(self, snapshots: list[VenueSnapshot], leads: list[LeadLagObservation]) -> None:
        path = self.data_dir / "observations.jsonl"
        row = {
            "local_ts_ms": int(time.time() * 1000),
            "snapshots": [asdict(x) for x in snapshots],
            "lead_lag": [asdict(x) for x in leads],
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def close(self) -> None:
        for client in self.clients.values():
            try:
                client.close()
            except Exception:
                pass
