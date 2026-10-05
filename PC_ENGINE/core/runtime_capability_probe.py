from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RuntimeProbeResult:
    venue: str
    capability: str
    environment: str
    verified: bool
    evidence: str
    risk_level: str


class RuntimeProbeBlocked(RuntimeError):
    pass


def run_read_only_probe(
    adapter: Any,
    *,
    capability: str,
    probe: Callable[[], Any],
    environment: str,
) -> RuntimeProbeResult:
    env = str(environment).upper()
    venue = str(getattr(adapter, "name", adapter.__class__.__name__))

    if env == "REAL" and capability not in {
        "market_data_historical",
        "market_data_realtime",
        "account_balances",
        "account_positions",
    }:
        raise RuntimeProbeBlocked(
            f"read-only runtime probe cannot verify write capability in {env}: {capability}"
        )

    try:
        result = probe()
    except Exception as exc:
        return RuntimeProbeResult(
            venue=venue,
            capability=capability,
            environment=env,
            verified=False,
            evidence=f"runtime_probe:error:{type(exc).__name__}:{exc}",
            risk_level="high" if env == "REAL" else "medium",
        )

    if result is None:
        return RuntimeProbeResult(
            venue=venue,
            capability=capability,
            environment=env,
            verified=False,
            evidence="runtime_probe:empty_response",
            risk_level="high" if env == "REAL" else "medium",
        )

    return RuntimeProbeResult(
        venue=venue,
        capability=capability,
        environment=env,
        verified=True,
        evidence=f"runtime_probe:success:{type(result).__name__}",
        risk_level="low" if capability.startswith("market_data_") else "medium",
    )
