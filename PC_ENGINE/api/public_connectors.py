from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from flask import Flask, jsonify, request


_FORBIDDEN_REQUEST_KEYS = frozenset({
    "api_key",
    "apikey",
    "secret",
    "api_secret",
    "password",
    "passphrase",
    "authorization",
    "access_token",
    "token",
    "refresh_token",
    "private_key",
    "cookie",
    "signature",
})


def _contains_forbidden_key(value: Any, *, depth: int = 0) -> bool:
    if depth > 8:
        return True
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _FORBIDDEN_REQUEST_KEYS:
                return True
            if _contains_forbidden_key(child, depth=depth + 1):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item, depth=depth + 1) for item in value)
    return False


def register_public_connector_routes(
    app: Flask,
    engine: Any,
    *,
    require_scope: Callable[[str], Any],
) -> None:
    """Expose only owner-authenticated, read-only public connector operations."""

    @app.get("/connectors")
    def public_connectors():
        require_scope("read_private_state")
        registry = getattr(engine, "connector_registry", None)
        if registry is None:
            response = jsonify({"ok": False, "error": "connector_runtime_unavailable"})
            response.status_code = 503
        else:
            response = jsonify({
                "ok": True,
                "connectors": registry.list_connectors(),
                "runtime": dict(getattr(engine, "connector_registry_status", {}) or {}),
                "paper_only": bool(getattr(engine, "paper", True)),
                "execution_authority": False,
            })
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.post("/connectors/<provider_id>/read")
    def public_connector_read(provider_id: str):
        require_scope("read_private_state")

        collector = getattr(engine, "paper_collector", None)
        collector_stopping = bool(
            getattr(getattr(collector, "stop_event", None), "is_set", lambda: False)()
        )
        if (
            str(getattr(getattr(engine, "state", None), "status", "OFF")).upper() != "RUNNING"
            or collector_stopping
        ):
            response = jsonify({"ok": False, "error": "engine_not_running"})
            response.status_code = 503
            response.headers["Cache-Control"] = "no-store"
            return response

        registry = getattr(engine, "connector_registry", None)
        if registry is None:
            response = jsonify({"ok": False, "error": "connector_runtime_unavailable"})
            response.status_code = 503
            response.headers["Cache-Control"] = "no-store"
            return response

        if request.content_length is not None and request.content_length > 32_768:
            response = jsonify({"ok": False, "error": "request_too_large"})
            response.status_code = 413
            response.headers["Cache-Control"] = "no-store"
            return response
        if not request.is_json:
            response = jsonify({"ok": False, "error": "json_body_required"})
            response.status_code = 415
            response.headers["Cache-Control"] = "no-store"
            return response

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or set(payload) - {"capability", "request"}:
            response = jsonify({"ok": False, "error": "invalid_request"})
            response.status_code = 400
            response.headers["Cache-Control"] = "no-store"
            return response

        capability = payload.get("capability")
        connector_request = payload.get("request", {})
        if not isinstance(connector_request, dict):
            response = jsonify({"ok": False, "error": "invalid_request"})
            response.status_code = 400
            response.headers["Cache-Control"] = "no-store"
            return response
        if _contains_forbidden_key(connector_request):
            response = jsonify({"ok": False, "error": "credential_fields_not_accepted"})
            response.status_code = 400
            response.headers["Cache-Control"] = "no-store"
            return response

        result = registry.execute_read(provider_id, capability, connector_request)
        status_codes = {
            "connector_not_found": 404,
            "capability_not_read_only": 403,
            "capability_not_authorized": 403,
            "rate_limited": 429,
            "request_too_large": 413,
            "invalid_request": 400,
            "request_not_json_serializable": 400,
            "response_too_large": 502,
            "connector_execution_failed": 502,
        }
        body = {
            "ok": bool(result.ok),
            "provider_id": result.provider_id,
            "capability": result.capability,
            "paper_only": bool(getattr(engine, "paper", True)),
            "execution_authority": False,
        }
        if result.ok:
            body["data"] = dict(result.data or {})
            status_code = 200
        else:
            body["error"] = result.error or "connector_execution_failed"
            status_code = status_codes.get(result.error or "", 502)

        response = jsonify(body)
        response.status_code = status_code
        response.headers["Cache-Control"] = "no-store"
        return response
