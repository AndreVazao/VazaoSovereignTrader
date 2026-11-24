from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


BOOK_FILES = {
    "binance": "binance_synchronized_orderbook_views.jsonl",
    "coinbase": "coinbase_synchronized_orderbook_views.jsonl",
    "okx": "okx_synchronized_orderbook_views.jsonl",
}


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _valid_levels(raw: Any, *, descending: bool, limit: int) -> list[tuple[float, float]] | None:
    if not isinstance(raw, list) or not raw or len(raw) > limit:
        return None
    levels: list[tuple[float, float]] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        price = _finite(item.get("price"))
        quantity = _finite(item.get("quantity"))
        if price is None or quantity is None or price <= 0 or quantity <= 0:
            return None
        levels.append((price, quantity))
    prices = [price for price, _ in levels]
    if len(prices) != len(set(prices)):
        return None
    if prices != sorted(prices, reverse=descending):
        return None
    return levels


def _fill(levels: list[tuple[float, float]], quantity: float) -> dict[str, Any]:
    remaining = quantity
    filled = 0.0
    notional = 0.0
    consumed = 0
    for price, available in levels:
        if remaining <= 0:
            break
        take = min(remaining, available)
        if take <= 0:
            continue
        filled += take
        notional += take * price
        remaining -= take
        consumed += 1
    return {
        "requested_quantity": quantity,
        "filled_quantity": filled,
        "vwap": notional / filled if filled > 0 else None,
        "filled_notional": notional,
        "consumed_levels": consumed,
        "full_fill": remaining <= max(1e-12, quantity * 1e-12),
    }


def analyze_book(
    row: dict[str, Any],
    *,
    quote_notional: float = 100.0,
    fee_bps: float = 0.0,
    max_age_ms: float = 1000.0,
    max_levels_per_side: int = 5000,
) -> dict[str, Any] | None:
    """Validate one persisted synchronized view and estimate depth execution cost.

    age_ms is the synchronizer's captured age at persistence time. The monotonic
    observation timestamp is retained as provenance and is never compared with
    a monotonic clock from a different process or machine.
    """
    if row.get("analysis_eligible") is not True or row.get("quality_status") != "VALID":
        return None
    if (
        row.get("paper_only") is not True
        or row.get("orders_submitted") is not False
        or row.get("execution_authorized") is not False
    ):
        return None
    if row.get("status") != "SYNCED":
        return None

    venue = row.get("venue")
    symbol = row.get("symbol")
    sequence = row.get("sequence", row.get("update_id"))
    observation_ns = row.get("observation_time_ns")
    age_ms = _finite(row.get("age_ms"))
    if (
        not isinstance(venue, str) or not venue.strip()
        or not isinstance(symbol, str) or not symbol.strip()
        or not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0
        or not isinstance(observation_ns, int) or isinstance(observation_ns, bool) or observation_ns <= 0
        or age_ms is None or age_ms < 0 or age_ms > max_age_ms
    ):
        return None

    bids = _valid_levels(row.get("bids"), descending=True, limit=max_levels_per_side)
    asks = _valid_levels(row.get("asks"), descending=False, limit=max_levels_per_side)
    if bids is None or asks is None or bids[0][0] >= asks[0][0]:
        return None

    best_bid, best_ask = bids[0][0], asks[0][0]
    mid = (best_bid + best_ask) / 2.0
    spread_bps = (best_ask - best_bid) / mid * 10_000.0
    buy_quantity = quote_notional / best_ask
    sell_quantity = quote_notional / best_bid
    buy = _fill(asks, buy_quantity)
    sell = _fill(bids, sell_quantity)
    buy_impact = None if buy["vwap"] is None else (buy["vwap"] / mid - 1.0) * 10_000.0
    sell_impact = None if sell["vwap"] is None else (1.0 - sell["vwap"] / mid) * 10_000.0
    total_depth = math.fsum(qty for _, qty in bids) + math.fsum(qty for _, qty in asks)
    imbalance = (
        (math.fsum(qty for _, qty in bids) - math.fsum(qty for _, qty in asks)) / total_depth
        if total_depth > 0 else None
    )
    return {
        "venue": venue.strip().lower(),
        "symbol": symbol.strip().upper(),
        "sequence": sequence,
        "observation_time_ns": observation_ns,
        "captured_age_ms": age_ms,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid,
        "spread_bps": spread_bps,
        "depth_imbalance": imbalance,
        "bid_levels": len(bids),
        "ask_levels": len(asks),
        "buy": buy,
        "sell": sell,
        "buy_impact_bps": buy_impact,
        "sell_impact_bps": sell_impact,
        "buy_cost_including_fee_bps": None if buy_impact is None else buy_impact + fee_bps,
        "sell_cost_including_fee_bps": None if sell_impact is None else sell_impact + fee_bps,
        "fee_assumption_bps_per_side": fee_bps,
        "quote_notional_assumption": quote_notional,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }


def _average(values: list[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def build_report(
    data_dir: str | Path,
    *,
    venues: tuple[str, ...] = ("binance", "coinbase", "okx"),
    quote_notional: float = 100.0,
    fee_bps: float = 0.0,
    max_age_ms: float = 1000.0,
    max_records: int = 100000,
    max_levels_per_side: int = 5000,
) -> dict[str, Any]:
    if not math.isfinite(quote_notional) or quote_notional <= 0:
        raise ValueError("quote_notional_must_be_finite_and_positive")
    if not math.isfinite(fee_bps) or fee_bps < 0:
        raise ValueError("fee_bps_must_be_finite_and_non_negative")
    if not math.isfinite(max_age_ms) or max_age_ms <= 0:
        raise ValueError("max_age_ms_must_be_finite_and_positive")
    if not isinstance(max_records, int) or isinstance(max_records, bool) or not 1 <= max_records <= 1_000_000:
        raise ValueError("max_records_out_of_range")
    if not isinstance(max_levels_per_side, int) or isinstance(max_levels_per_side, bool) or not 1 <= max_levels_per_side <= 5000:
        raise ValueError("max_levels_per_side_out_of_range")
    unknown = set(venues) - set(BOOK_FILES)
    if unknown:
        raise ValueError("unsupported_venue")

    started = time.time()
    samples: deque[dict[str, Any]] = deque(maxlen=max_records)
    counters = {
        "raw_lines_seen": 0,
        "malformed_json_ignored": 0,
        "non_object_rows_ignored": 0,
        "quality_flagged_ignored": 0,
        "non_paper_rows_ignored": 0,
        "invalid_or_stale_books_ignored": 0,
        "valid_books_analyzed": 0,
        "records_omitted_by_limit": 0,
        "files_missing": 0,
    }
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "samples": 0, "full_buy_fills": 0, "partial_buy_fills": 0,
        "full_sell_fills": 0, "partial_sell_fills": 0,
        "spreads": [], "buy_impacts": [], "sell_impacts": [],
        "buy_costs": [], "sell_costs": [], "imbalances": [],
    })
    root = Path(data_dir)

    for venue in venues:
        path = root / BOOK_FILES[venue]
        if not path.is_file():
            counters["files_missing"] += 1
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                counters["raw_lines_seen"] += 1
                try:
                    row = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    counters["malformed_json_ignored"] += 1
                    continue
                if not isinstance(row, dict):
                    counters["non_object_rows_ignored"] += 1
                    continue
                if row.get("analysis_eligible") is not True or row.get("quality_status") != "VALID":
                    counters["quality_flagged_ignored"] += 1
                    continue
                if (
                    row.get("paper_only") is not True
                    or row.get("orders_submitted") is not False
                    or row.get("execution_authorized") is not False
                ):
                    counters["non_paper_rows_ignored"] += 1
                    continue
                sample = analyze_book(
                    row, quote_notional=quote_notional, fee_bps=fee_bps,
                    max_age_ms=max_age_ms, max_levels_per_side=max_levels_per_side,
                )
                if sample is None:
                    counters["invalid_or_stale_books_ignored"] += 1
                    continue
                counters["valid_books_analyzed"] += 1
                if len(samples) == max_records:
                    counters["records_omitted_by_limit"] += 1
                samples.append(sample)
                key = f'{sample["venue"]}:{sample["symbol"]}'
                group = groups[key]
                group["samples"] += 1
                group["full_buy_fills"] += int(sample["buy"]["full_fill"])
                group["partial_buy_fills"] += int(0 < sample["buy"]["filled_quantity"] < sample["buy"]["requested_quantity"])
                group["full_sell_fills"] += int(sample["sell"]["full_fill"])
                group["partial_sell_fills"] += int(0 < sample["sell"]["filled_quantity"] < sample["sell"]["requested_quantity"])
                group["spreads"].append(sample["spread_bps"])
                if sample["buy_impact_bps"] is not None:
                    group["buy_impacts"].append(sample["buy_impact_bps"])
                    group["buy_costs"].append(sample["buy_cost_including_fee_bps"])
                if sample["sell_impact_bps"] is not None:
                    group["sell_impacts"].append(sample["sell_impact_bps"])
                    group["sell_costs"].append(sample["sell_cost_including_fee_bps"])
                if sample["depth_imbalance"] is not None:
                    group["imbalances"].append(sample["depth_imbalance"])

    summaries = {}
    for key, group in sorted(groups.items()):
        summaries[key] = {
            "samples": group["samples"],
            "full_buy_fills": group["full_buy_fills"],
            "partial_buy_fills": group["partial_buy_fills"],
            "full_sell_fills": group["full_sell_fills"],
            "partial_sell_fills": group["partial_sell_fills"],
            "average_spread_bps": _average(group["spreads"]),
            "average_buy_impact_bps": _average(group["buy_impacts"]),
            "average_sell_impact_bps": _average(group["sell_impacts"]),
            "average_buy_cost_including_fee_bps": _average(group["buy_costs"]),
            "average_sell_cost_including_fee_bps": _average(group["sell_costs"]),
            "average_depth_imbalance": _average(group["imbalances"]),
        }

    return {
        "schema_version": 1,
        "status": "EMPTY" if counters["valid_books_analyzed"] == 0 else "PAPER_SYNCHRONIZED_L2_RESEARCH",
        "started_at": started,
        "finished_at": time.time(),
        "configuration": {
            "venues": list(venues), "quote_notional": quote_notional,
            "fee_bps_per_side": fee_bps, "max_age_ms": max_age_ms,
            "max_records": max_records, "max_levels_per_side": max_levels_per_side,
        },
        "counters": counters,
        "summaries": summaries,
        "samples": list(samples),
        "limitations": [
            "PAPER research only; no signals, orders, private credentials or LIVE authorization.",
            "VWAP and impact are depth-based estimates at the captured book, not guaranteed fills.",
            "Fee assumption is caller-supplied and is not fetched or verified by this report.",
            "Cross-venue edges are intentionally not calculated; canonical instrument equivalence remains a separate gate.",
            "Captured age_ms is used; monotonic timestamps are provenance and are not compared across process clock domains.",
            "Samples are bounded by max_records; group summaries cover every accepted row in the input files.",
        ],
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze persisted synchronized public L2 books for PAPER research.")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--output", default="PC_ENGINE/data/replay/synchronized_l2_research.json")
    parser.add_argument("--venues", nargs="+", choices=sorted(BOOK_FILES), default=["binance", "coinbase", "okx"])
    parser.add_argument("--quote-notional", type=float, default=100.0)
    parser.add_argument("--fee-bps", type=float, default=0.0, help="Explicit assumed fee in basis points per side.")
    parser.add_argument("--max-age-ms", type=float, default=1000.0)
    parser.add_argument("--max-records", type=int, default=100000)
    parser.add_argument("--max-levels-per-side", type=int, default=5000)
    args = parser.parse_args()
    report = build_report(
        args.data_dir, venues=tuple(args.venues), quote_notional=args.quote_notional,
        fee_bps=args.fee_bps, max_age_ms=args.max_age_ms,
        max_records=args.max_records, max_levels_per_side=args.max_levels_per_side,
    )
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    print(json.dumps({
        "status": report["status"], "counters": report["counters"],
        "summaries": report["summaries"], "output": str(target),
        "paper_only": True, "orders_submitted": False,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
