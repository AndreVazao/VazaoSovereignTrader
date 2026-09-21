from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SHARED_FIELDS = frozenset({
    "schema_version",
    "artifact_type",
    "strategy_id",
    "market",
    "regime",
    "horizon_seconds",
    "sample_count",
    "win_count",
    "win_rate",
    "mean_net_bps",
    "median_net_bps",
    "eligible",
    "created_at_ms",
    "producer_version",
    "artifact_id",
    "source_digest",
})


@dataclass(frozen=True)
class SharedIntelligenceArtifact:
    """Privacy-safe learning artifact; never carries financial state."""

    artifact_type: str
    strategy_id: str
    market: str
    regime: str
    horizon_seconds: int
    sample_count: int
    win_count: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    eligible: bool
    created_at_ms: int
    producer_version: str = "1"
    artifact_id: str = ""
    source_digest: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "artifact_type": self.artifact_type,
            "strategy_id": self.strategy_id,
            "market": self.market,
            "regime": self.regime,
            "horizon_seconds": self.horizon_seconds,
            "sample_count": self.sample_count,
            "win_count": self.win_count,
            "win_rate": self.win_rate,
            "mean_net_bps": self.mean_net_bps,
            "median_net_bps": self.median_net_bps,
            "eligible": self.eligible,
            "created_at_ms": self.created_at_ms,
            "producer_version": self.producer_version,
            "artifact_id": self.artifact_id,
            "source_digest": self.source_digest,
        }


class SharedIntelligenceStore:
    """Append-only local store ready for a future cloud sync adapter."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_public_artifact(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("artifact_must_be_object")
        unknown = set(payload) - SHARED_FIELDS
        if unknown:
            raise ValueError("private_or_unknown_fields:" + ",".join(sorted(unknown)))
        required = SHARED_FIELDS - {"producer_version"}
        missing = required - set(payload)
        if missing:
            raise ValueError("missing_fields:" + ",".join(sorted(missing)))
        if int(payload["sample_count"]) < 0 or int(payload["win_count"]) < 0:
            raise ValueError("invalid_counts")
        if int(payload["win_count"]) > int(payload["sample_count"]):
            raise ValueError("win_count_exceeds_samples")
        rate = float(payload["win_rate"])
        if not 0.0 <= rate <= 1.0:
            raise ValueError("invalid_win_rate")
        if not str(payload["strategy_id"]).strip():
            raise ValueError("strategy_id_required")
        artifact_id = str(payload.get("artifact_id", "")).strip()
        if artifact_id and len(artifact_id) > 128:
            raise ValueError("artifact_id_too_long")
        source_digest = str(payload.get("source_digest", "")).strip()
        if source_digest and (len(source_digest) != 64 or any(ch not in "0123456789abcdef" for ch in source_digest.lower())):
            raise ValueError("invalid_source_digest")
        return dict(payload)

    def append(self, artifact: SharedIntelligenceArtifact) -> str:
        payload = self.validate_public_artifact(artifact.to_public_dict())
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        existing = {row["sha256"] for row in self.read()} if self.path.exists() else set()
        if digest not in existing:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"artifact": payload, "sha256": digest}, sort_keys=True) + "\n")
        return digest

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                self.validate_public_artifact(row["artifact"])
                canonical = json.dumps(row["artifact"], sort_keys=True, separators=(",", ":"))
                if row.get("sha256") != hashlib.sha256(canonical.encode("utf-8")).hexdigest():
                    raise ValueError("artifact_integrity_mismatch")
                rows.append(row)
        return rows
