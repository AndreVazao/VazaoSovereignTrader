from __future__ import annotations

import json
import os
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
    """Small stdlib-only adapter for the authenticated shared-learning API."""

    def __init__(self, *, base_url: str | None = None, token: str | None = None, timeout_seconds: float = 5.0):
        self.base_url = (base_url or os.getenv("VST_SHARED_INTELLIGENCE_URL", "")).strip().rstrip("/")
        self.token = (token or os.getenv("VST_SHARED_INTELLIGENCE_TOKEN", "")).strip()
        self.timeout_seconds = max(0.5, min(float(timeout_seconds), 15.0))
        if not self.base_url or not self.token:
            raise ValueError("shared_intelligence_cloud_not_configured")
        if not self.base_url.startswith("https://"):
            raise ValueError("shared_intelligence_requires_https")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.base_url + path
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url, data=data, method=method,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json",
                     **({"Content-Type": "application/json"} if data is not None else {})},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(256 * 1024 + 1)
                if len(raw) > 256 * 1024:
                    raise ValueError("shared_intelligence_response_too_large")
                parsed = json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("shared_intelligence_network_unavailable") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("shared_intelligence_invalid_response") from exc
        if not isinstance(parsed, dict) or parsed.get("ok") is not True:
            raise RuntimeError("shared_intelligence_api_rejected_request")
        return parsed

    def pull(self, *, cursor: str | None, limit: int) -> dict[str, Any]:
        # The current API offers a bounded snapshot, not cursor pagination.
        bounded_limit = max(1, min(int(limit), 100))
        response = self._request("GET", "/api/v1/artifacts?limit=" + str(bounded_limit))
        artifacts = response.get("artifacts", [])
        if not isinstance(artifacts, list):
            raise RuntimeError("shared_intelligence_invalid_artifact_list")
        return {"rows": [{"artifact": item} for item in artifacts], "next_cursor": ""}

    def push(self, *, rows: list[dict[str, Any]]) -> dict[str, Any]:
        accepted = 0
        now_ms = __import__("time").time_ns() // 1_000_000
        # Bound each maintenance pass; retrying is safe because the server deduplicates by owner + digest.
        for row in rows[:100]:
            artifact = row.get("artifact") if isinstance(row, dict) else None
            if not isinstance(artifact, dict):
                continue
            # Explicit allow-list: owner/node provenance stays local and is never transmitted.
            payload = {key: artifact[key] for key in CLOUD_FIELDS if key in artifact}
            if payload.get("eligible") is not True or int(payload.get("expires_at_ms", 0) or 0) <= now_ms:
                continue
            response = self._request("POST", "/api/v1/artifacts", payload)
            if response.get("accepted") is True:
                accepted += 1
        return {"accepted": accepted, "next_cursor": ""}
