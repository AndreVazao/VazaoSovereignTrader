from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class CapabilityVerification:
    venue: str
    capability: str
    environment: str
    declared: bool
    verified: bool
    evidence: str
    risk_level: str


_METHOD_CAPABILITIES = {
    "market_data_historical": ("fetch_ohlcv",),
    "market_data_realtime": ("fetch_ticker",),
    "account_balances": ("fetch_balance", "free_quote_balance"),
    "paper_order_submit": ("market_buy", "market_sell"),
    "paper_order_cancel": ("fetch_open_orders",),
    "real_order_submit": ("market_buy_with_client_order_id", "market_sell_with_client_order_id"),
    "real_order_cancel": ("cancel_order",),
    "account_positions": ("fetch_positions",),
}


def verify_adapter_contract(adapter: Any, environment: str) -> list[CapabilityVerification]:
    env = str(environment).upper()
    venue = str(getattr(adapter, "name", adapter.__class__.__name__))
    results: list[CapabilityVerification] = []

    for capability, methods in _METHOD_CAPABILITIES.items():
        present = [name for name in methods if callable(getattr(adapter, name, None))]
        declared = len(present) == len(methods)

        if capability == "market_data_websocket":
            declared = callable(getattr(adapter, "watch_ticker", None))

        verified = declared
        risk = "low" if capability.startswith("market_data_") else "medium"

        if env == "REAL" and capability in {"real_order_submit", "real_order_cancel", "capital_transfer"}:
            # Structural support is never sufficient evidence for capital movement.
            # REAL capabilities must later be promoted by an explicit runtime probe.
            verified = False
            risk = "critical"

        evidence = (
            "adapter_contract:" + ",".join(present)
            if present
            else "adapter_contract:missing_required_methods"
        )
        if capability == "market_data_websocket":
            evidence = "adapter_contract:watch_ticker" if declared else "adapter_contract:no_websocket_interface"

        results.append(
            CapabilityVerification(
                venue=venue,
                capability=capability,
                environment=env,
                declared=declared,
                verified=verified,
                evidence=evidence,
                risk_level=risk,
            )
        )

    return results
