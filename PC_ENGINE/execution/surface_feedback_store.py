from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .surface_adapters import SurfaceFeedback, feedback_record


class ExecutionSurfaceFeedbackStore:
    """Bounded local persistence for transport feedback.

    This store is operational telemetry only. It never authorizes execution.
    Writes are atomic and the retained record count is bounded.
    """

    _DOWN_STATES = {
        "DOWN", "DISCONNECTED", "ADB_UNAVAILABLE", "NO_DEVICE",
        "DEVICE_UNAUTHORIZED", "DEVICE_OFFLINE", "COMMUNICATION_ERROR",
    }
    _HEALTHY_STATES = {"CONNECTED", "READY", "OBSERVED", "APP_OBSERVED"}

    def __init__(self, path: str | Path, *, max_records: int = 2_000) -> None:
        if max_records < 1:
            raise ValueError("max_records must be positive")
        self.path = Path(path)
        self.max_records = int(max_records)
        self._write_errors = 0
        self._health_path = self.path.with_suffix(self.path.suffix + ".health.json")

    def append(self, feedback: SurfaceFeedback | dict[str, Any]) -> bool:
        record = feedback_record(feedback) if isinstance(feedback, SurfaceFeedback) else dict(feedback)
        record["stored_at_ms"] = int(time.time() * 1000)
        record["paper_only"] = True
        record["orders_submitted"] = False
        record["execution_authorized"] = False
        try:
            records = self._load()
            records.append(record)
            records = records[-self.max_records :]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(
                "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records),
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
            self._write_errors = 0
            self._persist_write_health(status="HEALTHY", write_errors=0, last_error=None)
            return True
        except (OSError, TypeError, ValueError) as exc:
            self._write_errors += 1
            self._persist_write_health(
                status="DEGRADED",
                write_errors=self._write_errors,
                last_error=f"{type(exc).__name__}: {exc}",
            )
            try:
                tmp = self.path.with_suffix(self.path.suffix + ".tmp")
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(item, dict):
                    records.append(item)
        return records[-self.max_records :]

    def _persist_write_health(self, *, status: str, write_errors: int, last_error: str | None) -> None:
        payload = {
            "status": status,
            "write_errors": max(0, int(write_errors)),
            "last_error": last_error,
            "updated_at_ms": int(time.time() * 1000),
        }
        try:
            self._health_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._health_path.with_suffix(self._health_path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(tmp, self._health_path)
        except (OSError, TypeError, ValueError):
            try:
                tmp = self._health_path.with_suffix(self._health_path.suffix + ".tmp")
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _persisted_write_health(self) -> dict[str, Any]:
        try:
            payload = json.loads(self._health_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def snapshot(self, *, stale_after_ms: int = 30_000) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        records = self._load()
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        reconnects: dict[tuple[str, str], int] = {}
        previous_state: dict[tuple[str, str], str] = {}

        for item in records:
            if item.get("paper_only") is not True or item.get("execution_authorized") is not False:
                continue
            key = (str(item.get("venue_id", "")), str(item.get("surface", "")))
            if not key[0] or not key[1]:
                continue
            state = str(item.get("state", "UNKNOWN")).upper()
            if state in self._HEALTHY_STATES and previous_state.get(key) in self._DOWN_STATES:
                reconnects[key] = reconnects.get(key, 0) + 1
            previous_state[key] = state
            latest[key] = item

        rows = []
        for (venue_id, surface), item in sorted(latest.items()):
            observed_at = int(item.get("observed_at_ms", 0) or 0)
            age = max(0, now_ms - observed_at) if observed_at > 0 else None
            state = str(item.get("state", "UNKNOWN")).upper()
            if state in self._DOWN_STATES:
                operational_state = "DOWN"
            elif state not in self._HEALTHY_STATES or age is None or age > stale_after_ms:
                operational_state = "DEGRADED"
            else:
                operational_state = "HEALTHY"
            rows.append({
                "venue_id": venue_id,
                "surface": surface,
                "state": operational_state,
                "connection_state": state,
                "last_feedback_age_ms": age,
                "last_feedback_at_ms": observed_at or None,
                "reconnects": reconnects.get((venue_id, surface), 0),
                "acknowledged": bool(item.get("acknowledged", False)),
                "detail": str(item.get("detail", "")),
                "request_id": str(item.get("request_id", "")),
                "source": "persistent_feedback",
                "live_probe": True,
                "paper_only": True,
                "orders_submitted": False,
                "execution_authorized": False,
            })

        persisted_health = self._persisted_write_health()
        persisted_status = str(persisted_health.get("status", "")).upper()
        persisted_errors = int(persisted_health.get("write_errors", 0) or 0)
        write_errors = max(self._write_errors, persisted_errors)
        data_write_health = (
            "DEGRADED"
            if self._write_errors > 0 or persisted_status == "DEGRADED" or persisted_errors > 0
            else "HEALTHY"
        )

        return {
            "operational_only": True,
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
            "feedback_path": str(self.path),
            "records_retained": len(records),
            "max_records": self.max_records,
            "data_write_health": data_write_health,
            "write_errors": write_errors,
            "last_write_error": persisted_health.get("last_error"),
            "write_health_path": str(self._health_path),
            "surfaces": rows,
        }
