from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CapitalTransferIntent:
    intent_id: str
    owner_id: str
    source_venue: str
    destination_venue: str
    asset: str
    network: str
    amount_quote: float
    estimated_cost_quote: float
    expected_net_edge_bps: float
    state: str
    created_at_ms: int


class CapitalTransferIntentStore:
    """Durable owner-private transfer intents without transfer execution."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @staticmethod
    def _intent_id(
        owner_id: str,
        source_venue: str,
        destination_venue: str,
        asset: str,
        network: str,
        amount_quote: float,
    ) -> str:
        raw = "|".join(
            [
                owner_id,
                source_venue.lower(),
                destination_venue.lower(),
                asset.upper(),
                network.upper(),
                f"{amount_quote:.12f}",
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def create(
        self,
        *,
        owner_id: str,
        source_venue: str,
        destination_venue: str,
        asset: str,
        network: str,
        amount_quote: float,
        estimated_cost_quote: float,
        expected_net_edge_bps: float,
    ) -> CapitalTransferIntent:
        if not owner_id:
            raise ValueError("owner_id is required")
        if not source_venue or not destination_venue or source_venue == destination_venue:
            raise ValueError("invalid venue route")
        if not asset or not network:
            raise ValueError("asset and network are required")
        if amount_quote <= 0:
            raise ValueError("amount_quote must be positive")
        if estimated_cost_quote < 0:
            raise ValueError("estimated_cost_quote must be non-negative")

        intent = CapitalTransferIntent(
            intent_id=self._intent_id(
                owner_id, source_venue, destination_venue, asset, network, amount_quote
            ),
            owner_id=owner_id,
            source_venue=source_venue.lower(),
            destination_venue=destination_venue.lower(),
            asset=asset.upper(),
            network=network.upper(),
            amount_quote=float(amount_quote),
            estimated_cost_quote=float(estimated_cost_quote),
            expected_net_edge_bps=float(expected_net_edge_bps),
            state="PLANNED",
            created_at_ms=int(time.time() * 1000),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = self._existing_ids()
        if intent.intent_id not in existing:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(intent), sort_keys=True) + "\n")
        return intent

    def _existing_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        ids: set[str] = set()
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                    if row.get("intent_id"):
                        ids.add(str(row["intent_id"]))
                except json.JSONDecodeError:
                    continue
        return ids

    def snapshot(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "owner_private": True,
            "execution_authority": "NONE",
            "states": ["PLANNED"],
        }
