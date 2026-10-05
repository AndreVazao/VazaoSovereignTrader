from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


TERMINAL_STATUSES = {"closed", "filled"}
OPEN_STATUSES = {"open", "new", "partially_filled", "partially-filled"}


@dataclass(frozen=True)
class NormalizedOrder:
    venue_order_id: str
    client_order_id: str | None
    status: str
    side: str
    symbol: str
    requested_qty: float
    filled_qty: float
    average_price: float
    fee: float
    fee_currency: str | None


class AdapterContractError(ValueError):
    """Raised when an exchange adapter returns unsafe or ambiguous order data."""


def normalize_order_response(
    raw: dict[str, Any],
    *,
    symbol: str,
    side: str,
    requested_qty: float,
    fallback_price: float,
) -> NormalizedOrder:
    if not isinstance(raw, dict):
        raise AdapterContractError("adapter order response must be a mapping")

    order_id = str(raw.get("id") or "").strip()
    if not order_id:
        raise AdapterContractError("adapter order response missing venue order id")

    status_raw = str(raw.get("status") or "").strip().lower()
    if status_raw in TERMINAL_STATUSES:
        status = "FILLED"
    elif status_raw in OPEN_STATUSES:
        status = "PENDING_OR_PARTIAL"
    else:
        raise AdapterContractError(f"unsupported or unknown order status: {status_raw or 'missing'}")

    filled_raw = raw.get("filled")
    amount_raw = raw.get("amount")
    if filled_raw is None:
        filled_raw = amount_raw if status == "FILLED" else 0.0
    try:
        filled = float(filled_raw)
    except (TypeError, ValueError) as exc:
        raise AdapterContractError("filled quantity is not numeric") from exc
    if not math.isfinite(filled) or filled < 0:
        raise AdapterContractError("filled quantity is non-finite or negative")
    if filled > float(requested_qty) + 1e-12:
        raise AdapterContractError("filled quantity exceeds requested quantity")

    price_raw = raw.get("average")
    if price_raw is None:
        price_raw = raw.get("price")
    if price_raw is None:
        price_raw = fallback_price
    try:
        average_price = float(price_raw)
    except (TypeError, ValueError) as exc:
        raise AdapterContractError("average price is not numeric") from exc
    if not math.isfinite(average_price) or average_price <= 0:
        raise AdapterContractError("average price is non-finite or non-positive")

    fee = raw.get("fee")
    fees = raw.get("fees")
    fee_items = []
    if isinstance(fee, dict):
        fee_items.append(fee)
    if isinstance(fees, list):
        fee_items.extend(item for item in fees if isinstance(item, dict))

    fee_total = 0.0
    fee_currency: str | None = None
    _, quote = symbol.split("/", 1)
    base, _ = symbol.split("/", 1)
    for item in fee_items:
        try:
            cost = float(item.get("cost") or 0.0)
        except (TypeError, ValueError) as exc:
            raise AdapterContractError("fee cost is not numeric") from exc
        if not math.isfinite(cost) or cost < 0:
            raise AdapterContractError("fee cost is non-finite or negative")
        currency = str(item.get("currency") or "").strip()
        if currency == base:
            cost *= average_price
        elif currency and currency != quote:
            raise AdapterContractError(f"fee currency outside base/quote: {currency}")
        fee_total += cost
        fee_currency = currency or fee_currency

    client_order_id = str(
        raw.get("clientOrderId") or raw.get("client_order_id") or ""
    ).strip() or None

    return NormalizedOrder(
        venue_order_id=order_id,
        client_order_id=client_order_id,
        status=status,
        side=str(side).lower(),
        symbol=str(symbol),
        requested_qty=float(requested_qty),
        filled_qty=filled,
        average_price=average_price,
        fee=fee_total,
        fee_currency=fee_currency,
    )
