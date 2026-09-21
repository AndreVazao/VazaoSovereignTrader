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
    "source_owner_ref",
    "source_node_ref",
    "trust_score",
    "source_count",
    "expires_at_ms",
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
    source_owner_ref: str = ""
    source_node_ref: str = ""
    trust_score: float = 0.0
    source_count: int = 1
    expires_at_ms: int = 0

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
            "source_owner_ref": self.source_owner_ref,
            "source_node_ref": self.source_node_ref,
            "trust_score": self.trust_score,
            "source_count": self.source_count,
            "expires_at_ms": self.expires_at_ms,
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
        trust_score = float(payload.get("trust_score", 0.0))
        if not 0.0 <= trust_score <= 1.0:
            raise ValueError("invalid_trust_score")
        source_count = int(payload.get("source_count", 1))
        if source_count < 1:
            raise ValueError("invalid_source_count")
        expires_at_ms = int(payload.get("expires_at_ms", 0))
        if expires_at_ms < 0:
            raise ValueError("invalid_expiry")
        for field in ("source_owner_ref", "source_node_ref"):
            if len(str(payload.get(field, ""))) > 128:
                raise ValueError("source_ref_too_long")
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


@dataclass(frozen=True)
class SharedIntelligenceImportResult:
    accepted: int
    rejected: int
    skipped: int


class SharedIntelligenceImporter:
    """Fail-closed advisory importer; never touches financial or execution state."""

    def __init__(self, store: SharedIntelligenceStore, *, max_age_ms: int = 86_400_000):
        self.store = store
        self.max_age_ms = max(1, int(max_age_ms))

    def import_rows(self, rows: list[dict[str, Any]], *, now_ms: int) -> SharedIntelligenceImportResult:
        accepted = rejected = skipped = 0
        for row in rows:
            try:
                payload = row.get("artifact", row) if isinstance(row, dict) else None
                if not isinstance(payload, dict):
                    rejected += 1
                    continue
                validated = self.store.validate_public_artifact(payload)
                supplied_digest = str(row.get("sha256", "")).strip()
                canonical = json.dumps(validated, sort_keys=True, separators=(",", ":"))
                expected_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if supplied_digest and supplied_digest != expected_digest:
                    rejected += 1
                    continue
                created_at_ms = int(validated["created_at_ms"])
                expires_at_ms = int(validated.get("expires_at_ms", 0) or 0)
                if created_at_ms <= 0 or now_ms - created_at_ms > self.max_age_ms:
                    skipped += 1
                    continue
                if expires_at_ms and now_ms >= expires_at_ms:
                    skipped += 1
                    continue
                if now_ms < created_at_ms:
                    skipped += 1
                    continue
                self.store.append(
                    SharedIntelligenceArtifact(
                        artifact_type=str(validated["artifact_type"]),
                        strategy_id=str(validated["strategy_id"]),
                        market=str(validated["market"]),
                        regime=str(validated["regime"]),
                        horizon_seconds=int(validated["horizon_seconds"]),
                        sample_count=int(validated["sample_count"]),
                        win_count=int(validated["win_count"]),
                        win_rate=float(validated["win_rate"]),
                        mean_net_bps=float(validated["mean_net_bps"]),
                        median_net_bps=float(validated["median_net_bps"]),
                        eligible=bool(validated["eligible"]),
                        created_at_ms=created_at_ms,
                        producer_version=str(validated.get("producer_version", "1")),
                        artifact_id=str(validated.get("artifact_id", "")),
                        source_digest=str(validated.get("source_digest", "")),
                        source_owner_ref=str(validated.get("source_owner_ref", "")),
                        source_node_ref=str(validated.get("source_node_ref", "")),
                        trust_score=float(validated.get("trust_score", 0.0)),
                        source_count=int(validated.get("source_count", 1)),
                        expires_at_ms=int(validated.get("expires_at_ms", 0)),
                    )
                )
                accepted += 1
            except (TypeError, ValueError, KeyError, OverflowError):
                rejected += 1
        return SharedIntelligenceImportResult(accepted, rejected, skipped)
