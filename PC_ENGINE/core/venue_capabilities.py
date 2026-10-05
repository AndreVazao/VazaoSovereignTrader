from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


CAPABILITY_NAMES = (
    "market_data_historical",
    "market_data_websocket",
    "market_data_realtime",
    "account_balances",
    "account_positions",
    "paper_order_submit",
    "paper_order_cancel",
    "real_order_submit",
    "real_order_cancel",
    "capital_transfer",
)


@dataclass(frozen=True)
class VenueCapability:
    venue: str
    capability: str
    declared: bool
    verified: bool
    environment: str
    last_verified: str | None = None
    evidence: str | None = None
    risk_level: str = "unknown"

    @property
    def executable(self) -> bool:
        return self.declared and self.verified and self.environment in {"PAPER", "REAL"}


class VenueCapabilityRegistry:
    """Fail-closed capability registry; declarations never imply verification."""

    def __init__(self, config: dict[str, Any] | None = None):
        self._rows: dict[tuple[str, str, str], VenueCapability] = {}
        for venue, capabilities in (config or {}).items():
            if not isinstance(capabilities, dict):
                continue
            for capability, raw in capabilities.items():
                if not isinstance(raw, dict):
                    continue
                environment = str(raw.get("environment", "PAPER")).upper()
                self.register(
                    VenueCapability(
                        venue=str(venue),
                        capability=str(capability),
                        declared=bool(raw.get("declared", False)),
                        verified=bool(raw.get("verified", False)),
                        environment=environment,
                        last_verified=raw.get("last_verified"),
                        evidence=raw.get("evidence"),
                        risk_level=str(raw.get("risk_level", "unknown")),
                    )
                )

    def register(self, row: VenueCapability) -> None:
        key = (row.venue, row.capability, row.environment)
        self._rows[key] = row

    def get(self, venue: str, capability: str, environment: str) -> VenueCapability | None:
        return self._rows.get((str(venue), str(capability), str(environment).upper()))

    def verify_required(
        self,
        venues: list[str] | tuple[str, ...],
        capabilities: list[str] | tuple[str, ...],
        environment: str,
    ) -> tuple[bool, list[str]]:
        env = str(environment).upper()
        blockers: list[str] = []
        for venue in venues:
            for capability in capabilities:
                row = self.get(venue, capability, env)
                if row is None:
                    blockers.append(f"{venue}:{capability}:missing")
                elif not row.declared:
                    blockers.append(f"{venue}:{capability}:not_declared")
                elif not row.verified:
                    blockers.append(f"{venue}:{capability}:not_verified")
                elif row.environment != env:
                    blockers.append(f"{venue}:{capability}:wrong_environment")
        return not blockers, blockers

    def snapshot(self) -> list[dict[str, Any]]:
        return [asdict(row) for row in sorted(self._rows.values(), key=lambda x: (x.venue, x.environment, x.capability))]


def build_real_execution_requirements() -> tuple[str, ...]:
    return (
        "market_data_realtime",
        "account_balances",
        "account_positions",
        "real_order_submit",
        "real_order_cancel",
    )
