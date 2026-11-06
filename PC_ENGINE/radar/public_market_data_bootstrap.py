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
    require_all_exchanges: bool = True,
    minimum_ready_venues: int = 1,
) -> dict[str, Any]:
    """Verify public market-data access and persist a local bootstrap manifest.

    By default every configured venue must pass. A constrained or partially
    connected installation may instead require a minimum number of fully ready
    venues; all optional venue/symbol failures remain visible in the manifest.

    This operation is strictly public/read-only. It never loads private keys,
    calls balances, creates orders, or changes trading mode.
    """
    minimum_ready_venues = int(minimum_ready_venues)
    if minimum_ready_venues < 1:
        raise ValueError("minimum_ready_venues must be at least 1")

    exchange_names = list(dict.fromkeys(exchanges))
    symbol_names = list(dict.fromkeys(symbols))
    root = Path(__file__).resolve().parents[2]
    output_dir = _resolve_path(data_dir, root)
    output_path = output_dir / "market_data_bootstrap.json"
    started_ms = time.time_ns() // 1_000_000
    factory = client_factory or (lambda name: getattr(ccxt, name)({"enableRateLimit": True}))
    venues: list[dict[str, Any]] = []

    for exchange_name in exchange_names:
        venue = {
            "exchange": exchange_name,
            "status": "FAILED",
            "symbols": {},
            "ready_symbols": 0,
            "failed_symbols": len(symbol_names),
            "public_only": True,
            "private_credentials_used": False,
        }
        client = None
        try:
            client = factory(exchange_name)
            try:
                client.load_markets()
            except Exception:
                # Some public endpoints work even when market metadata is temporarily unavailable.
                pass
            for symbol in symbol_names:
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

            ready_symbols = sum(
                1 for row in venue["symbols"].values() if row.get("status") == "READY"
            )
            venue["ready_symbols"] = ready_symbols
            venue["failed_symbols"] = len(venue["symbols"]) - ready_symbols
            if venue["symbols"] and ready_symbols == len(venue["symbols"]):
                venue["status"] = "READY"
            elif ready_symbols:
                venue["status"] = "PARTIAL"
            else:
                venue["status"] = "DEGRADED"
        except Exception as exc:
            venue["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

        venues.append(venue)

    completed_ms = time.time_ns() // 1_000_000
    ready_venues = sum(1 for venue in venues if venue["status"] == "READY")
    partial_venues = [
        venue["exchange"] for venue in venues if venue["status"] == "PARTIAL"
    ]
    degraded_venues = [
        venue["exchange"] for venue in venues if venue["status"] != "READY"
    ]
    all_configured_venues_ready = bool(venues) and ready_venues == len(venues)
    if require_all_exchanges:
        readiness_satisfied = bool(venues) and all_configured_venues_ready
        readiness_policy = "ALL_CONFIGURED_EXCHANGES"
        effective_minimum_ready_venues = len(venues)
    else:
        readiness_satisfied = bool(venues) and ready_venues >= minimum_ready_venues
        readiness_policy = "MINIMUM_READY_VENUES"
        effective_minimum_ready_venues = minimum_ready_venues

    payload = {
        "schema_version": 2,
        "service": "public_market_data_bootstrap",
        "status": "READY" if readiness_satisfied else "DEGRADED",
        "readiness_policy": readiness_policy,
        "require_all_exchanges": bool(require_all_exchanges),
        "minimum_ready_venues": effective_minimum_ready_venues,
        "started_ms": started_ms,
        "completed_ms": completed_ms,
        "duration_ms": max(0, completed_ms - started_ms),
        "timeframe": timeframe,
        "candle_limit": candle_limit,
        "exchanges": exchange_names,
        "symbols": symbol_names,
        "ready_venues": ready_venues,
        "partial_venues": partial_venues,
        "degraded_venues": degraded_venues,
        "total_venues": len(venues),
        "ready_symbols_total": sum(int(venue["ready_symbols"]) for venue in venues),
        "all_configured_venues_ready": all_configured_venues_ready,
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
    policy = parser.add_mutually_exclusive_group()
    policy.add_argument(
        "--require-all-exchanges",
        action="store_true",
        help="Require every configured polling exchange to pass.",
    )
    policy.add_argument(
        "--minimum-ready-venues",
        type=int,
        default=None,
        help="Accept bootstrap when at least this many configured venues fully pass.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    config = json.loads(_resolve_path(args.config, root).read_text(encoding="utf-8"))
    radar = dict(config.get("radar", {}))
    bootstrap_cfg = dict(radar.get("bootstrap", {}))
    exchanges = [
        x.strip() for x in (args.exchanges or ",".join(radar.get("polling_exchanges", []))).split(",") if x.strip()
    ]
    symbols = [
        x.strip() for x in (args.symbols or ",".join(config.get("symbols", []))).split(",") if x.strip()
    ]
    data_dir = args.data_dir or radar.get("data_dir", "PC_ENGINE/data/radar")

    require_all_exchanges = bool(bootstrap_cfg.get("require_all_polling_exchanges", True))
    minimum_ready_venues = int(bootstrap_cfg.get("minimum_ready_venues", 1))
    if args.require_all_exchanges:
        require_all_exchanges = True
    elif args.minimum_ready_venues is not None:
        require_all_exchanges = False
        minimum_ready_venues = args.minimum_ready_venues

    report = bootstrap_public_market_data(
        exchanges=exchanges,
        symbols=symbols,
        data_dir=data_dir,
        timeframe=args.timeframe or config.get("strategy", {}).get("timeframe", "1m"),
        candle_limit=int(args.candle_limit or config.get("strategy", {}).get("candles_limit", 120)),
        require_all_exchanges=require_all_exchanges,
        minimum_ready_venues=minimum_ready_venues,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
