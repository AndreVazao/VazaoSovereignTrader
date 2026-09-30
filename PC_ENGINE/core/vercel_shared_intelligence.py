from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


CLOUD_FIELDS = (
    "schema_version", "artifact_type", "strategy_id", "market", "regime",
    "horizon_seconds", "sample_count", "win_count", "win_rate", "mean_net_bps",
    "median_net_bps", "eligible", "created_at_ms", "producer_version",
    "artifact_id", "source_digest", "trust_score", "source_count", "expires_at_ms",
)


class VercelSharedIntelligenceProvider:
    """Authenticated adapter for the allow-listed Vercel shared-learning API."""

    def __init__(self, base_url: str, token: str, *, timeout_seconds: float = 5.0):
        self.base_url = str(base_url).strip().rstrip("/")
        self.token = str(token).strip()
        self.timeout_seconds = max(0.5, min(float(timeout_seconds), 15.0))
        if not self.base_url or not self.token:
            raise ValueError("vercel_shared_intelligence_not_configured")
        if not self.base_url.startswith("https://"):
            raise ValueError("vercel_shared_intelligence_requires_https")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8") if payload is not None else None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(256 * 1024 + 1)
                if len(raw) > 256 * 1024:
                    raise RuntimeError("vercel_shared_intelligence_response_too_large")
                parsed = json.loads(raw.decode("utf-8") or "{}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("vercel_shared_intelligence_unavailable") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("vercel_shared_intelligence_invalid_response") from exc
        if not isinstance(parsed, dict) or parsed.get("ok") is not True:
            raise RuntimeError("vercel_shared_intelligence_api_rejected_request")
        return parsed

    def pull(self, *, cursor: str | None, limit: int) -> dict[str, Any]:
        # The deployed route is a bounded snapshot endpoint; it does not expose cursors.
        bounded_limit = max(1, min(int(limit), 100))
        response = self._request(
            "GET", "/api/v1/artifacts?" + urllib.parse.urlencode({"limit": bounded_limit})
        )
        artifacts = response.get("artifacts", [])
        if not isinstance(artifacts, list):
            raise RuntimeError("vercel_shared_intelligence_invalid_artifacts")
        return {"rows": [{"artifact": item} for item in artifacts], "next_cursor": ""}

    def push(self, *, rows: list[dict[str, Any]]) -> dict[str, Any]:
        accepted = 0
        now_ms = time.time_ns() // 1_000_000
        # One request per artifact matches the API contract; retries are deduplicated server-side.
        for row in rows[:100]:
            artifact = row.get("artifact") if isinstance(row, dict) else None
            if not isinstance(artifact, dict):
                continue
            # Never transmit local owner/device provenance; only these public fields can leave the PC.
            payload = {key: artifact[key] for key in CLOUD_FIELDS if key in artifact}
            if payload.get("eligible") is not True:
                continue
            try:
                if int(payload.get("expires_at_ms", 0)) <= now_ms:
                    continue
            except (TypeError, ValueError):
                continue
            response = self._request("POST", "/api/v1/artifacts", payload)
            if response.get("accepted") is True:
                accepted += 1
        return {"accepted": accepted, "next_cursor": ""}
