from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable

import ccxt

from PC_ENGINE.core.preflight import validate_ohlcv_rows


def _resolve_path(raw: str | Path, root: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def bootstrap_public_market_data(
    *,
    exchanges: list[str],
    symbols: list[str],
    data_dir: str | Path,
    timeframe: str = "1m",
    candle_limit: int = 120,
    client_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Verify public market-data access and persist a local bootstrap manifest.

    This operation is strictly public/read-only. It never loads private keys,
    calls balances, creates orders, or changes trading mode.
    """
    root = Path(__file__).resolve().parents[2]
    output_dir = _resolve_path(data_dir, root)
    output_path = output_dir / "market_data_bootstrap.json"
    started_ms = time.time_ns() // 1_000_000
    factory = client_factory or (lambda name: getattr(ccxt, name)({"enableRateLimit": True}))
    venues: list[dict[str, Any]] = []
    required_failures = 0

    for exchange_name in dict.fromkeys(exchanges):
        venue = {
            "exchange": exchange_name,
            "status": "FAILED",
            "symbols": {},
            "public_only": True,
            "private_credentials_used": False,
        }
        try:
            client = factory(exchange_name)
            try:
                client.load_markets()
            except Exception:
                # Some public endpoints work even when market metadata is temporarily unavailable.
                pass
            for symbol in dict.fromkeys(symbols):
                item: dict[str, Any] = {"status": "FAILED"}
                try:
                    ticker = client.fetch_ticker(symbol)
                    price = float(ticker.get("last") or 0.0)
                    item["ticker"] = {
                        "price": price,
                        "timestamp_ms": ticker.get("timestamp"),
                    }
                    candles = client.fetch_ohlcv(symbol, timeframe=timeframe, limit=candle_limit)
                    quality = validate_ohlcv_rows(
                        candles,
                        max_gap_seconds=None,
                        max_age_seconds=None,
                    )
                    item["ohlcv"] = {
                        "rows": len(candles),
                        "valid_rows": quality.valid_rows,
                        "quality_ok": quality.ok,
                        "errors": quality.errors[:10],
                    }
                    if price <= 0:
                        raise ValueError("public ticker returned a non-positive last price")
                    if not quality.ok or quality.valid_rows < min(30, candle_limit):
                        raise ValueError("public OHLCV failed the market-data quality gate")
                    item["status"] = "READY"
                except Exception as exc:
                    item["error"] = f"{type(exc).__name__}: {exc}"
                venue["symbols"][symbol] = item
            venue["status"] = (
                "READY"
                if venue["symbols"] and all(row.get("status") == "READY" for row in venue["symbols"].values())
                else "DEGRADED"
            )
        except Exception as exc:
            venue["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            close = locals().get("client")
            if close is not None:
                try:
                    close.close()
                except Exception:
                    pass

        if venue["status"] != "READY":
            required_failures += 1
        venues.append(venue)

    completed_ms = time.time_ns() // 1_000_000
    ready_venues = sum(1 for venue in venues if venue["status"] == "READY")
    payload = {
        "schema_version": 1,
        "service": "public_market_data_bootstrap",
        "status": "READY" if venues and required_failures == 0 else "DEGRADED",
        "started_ms": started_ms,
        "completed_ms": completed_ms,
        "duration_ms": max(0, completed_ms - started_ms),
        "timeframe": timeframe,
        "candle_limit": candle_limit,
        "exchanges": list(dict.fromkeys(exchanges)),
        "symbols": list(dict.fromkeys(symbols)),
        "ready_venues": ready_venues,
        "total_venues": len(venues),
        "public_only": True,
        "private_credentials_used": False,
        "orders_submitted": False,
        "execution_authorized": False,
        "venues": venues,
    }
    _atomic_json(output_path, payload)
    payload["report_path"] = str(output_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify public market-data access before PAPER startup.")
    parser.add_argument("--config", default="PC_ENGINE/config/config.local.json")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--exchanges", default=None)
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--candle-limit", type=int, default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    config = json.loads(_resolve_path(args.config, root).read_text(encoding="utf-8"))
    radar = dict(config.get("radar", {}))
    exchanges = [
        x.strip() for x in (args.exchanges or ",".join(radar.get("polling_exchanges", []))).split(",") if x.strip()
    ]
    symbols = [
        x.strip() for x in (args.symbols or ",".join(config.get("symbols", []))).split(",") if x.strip()
    ]
    data_dir = args.data_dir or radar.get("data_dir", "PC_ENGINE/data/radar")
    report = bootstrap_public_market_data(
        exchanges=exchanges,
        symbols=symbols,
        data_dir=data_dir,
        timeframe=args.timeframe or config.get("strategy", {}).get("timeframe", "1m"),
        candle_limit=int(args.candle_limit or config.get("strategy", {}).get("candles_limit", 120)),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
