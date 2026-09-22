from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CapitalTransferAccountingEntry:
    intent_id: str
    owner_id: str
    source_venue: str
    destination_venue: str
    asset: str
    amount: float
    source_delta: float
    destination_delta: float
    external_reference: str | None
    recorded_at_ms: int


class CapitalTransferAccounting:
    """Owner-private expected deltas applied exactly once after CONFIRMED."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _entries(self) -> dict[str, CapitalTransferAccountingEntry]:
        latest: dict[str, CapitalTransferAccountingEntry] = {}
        if not self.path.exists():
            return latest
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = CapitalTransferAccountingEntry(**json.loads(line))
                    latest[item.intent_id] = item
                except (json.JSONDecodeError, TypeError):
                    continue
        return latest

    def apply_confirmed(self, *, intent_id: str, owner_id: str, source_venue: str, destination_venue: str,
                        asset: str, amount: float, external_reference: str | None = None) -> CapitalTransferAccountingEntry:
        if not intent_id or not owner_id:
            raise ValueError("intent_id and owner_id are required")
        if not source_venue or not destination_venue or source_venue == destination_venue:
            raise ValueError("invalid venue route")
        if not asset or amount <= 0:
            raise ValueError("asset and positive amount are required")
        existing = self._entries().get(intent_id)
        if existing:
            if existing.owner_id != owner_id:
                raise PermissionError("transfer accounting belongs to another owner")
            return existing
        item = CapitalTransferAccountingEntry(
            intent_id=intent_id, owner_id=owner_id, source_venue=source_venue.lower(), destination_venue=destination_venue.lower(),
            asset=asset.upper(), amount=round(float(amount), 8), source_delta=round(-float(amount), 8),
            destination_delta=round(float(amount), 8), external_reference=external_reference,
            recorded_at_ms=int(time.time() * 1000),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
        return item

    def expected_deltas(self, *, owner_id: str) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for item in self._entries().values():
            if item.owner_id != owner_id:
                continue
            for venue, delta in ((item.source_venue, item.source_delta), (item.destination_venue, item.destination_delta)):
                bucket = result.setdefault(venue, {})
                bucket[item.asset] = round(bucket.get(item.asset, 0.0) + delta, 8)
        return result

    def reconcile_deltas(self, *, owner_id: str, observed_deltas: dict[str, dict[str, float]], tolerance: float = 1e-8) -> dict[str, Any]:
        if tolerance < 0:
            raise ValueError("tolerance must be non-negative")
        expected = self.expected_deltas(owner_id=owner_id)
        mismatches: list[dict[str, Any]] = []
        venues = set(expected) | {str(v).lower() for v in observed_deltas}
        for venue in sorted(venues):
            exp_assets = expected.get(venue, {})
            obs_assets = {str(k).upper(): float(v) for k, v in observed_deltas.get(venue, {}).items()}
            for asset in set(exp_assets) | set(obs_assets):
                exp, obs = float(exp_assets.get(asset, 0.0)), float(obs_assets.get(asset, 0.0))
                if abs(obs - exp) > tolerance:
                    mismatches.append({"venue": venue, "asset": asset, "expected_delta": exp, "observed_delta": obs})
        return {"owner_private": True, "reconciled": not mismatches, "mismatch_count": len(mismatches),
                "mismatches": mismatches, "expected_deltas": expected}

    def snapshot(self, *, owner_id: str | None = None) -> dict[str, Any]:
        entries = list(self._entries().values())
        if owner_id is not None:
            entries = [item for item in entries if item.owner_id == owner_id]
        return {"owner_private": True, "execution_authority": "NONE", "entries": [asdict(item) for item in entries]}
