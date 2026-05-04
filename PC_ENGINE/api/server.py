from __future__ import annotations

import os
from flask import Flask, jsonify, request

from PC_ENGINE.core.config import env_value
from PC_ENGINE.core.engine import SovereignEngine


def create_app(engine: SovereignEngine, token_env: str = "VST_LOCAL_TOKEN") -> Flask:
    app = Flask(__name__)

    def require_token() -> None:
        expected = env_value(token_env, "change-this-local-token")
        provided = request.headers.get("X-Token", "")
        if expected and provided != expected:
            raise PermissionError("unauthorized")

    @app.errorhandler(PermissionError)
    def handle_unauthorized(_: PermissionError):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    @app.get("/status")
    def status():
        require_token()
        return jsonify(engine.snapshot())

    @app.post("/start")
    def start():
        require_token()
        engine.start()
        return jsonify({"ok": True})

    @app.post("/pause")
    def pause():
        require_token()
        engine.pause(True)
        return jsonify({"ok": True})

    @app.post("/resume")
    def resume():
        require_token()
        engine.pause(False)
        return jsonify({"ok": True})

    @app.post("/stop")
    def stop():
        require_token()
        engine.stop()
        return jsonify({"ok": True})

    @app.post("/mode")
    def mode():
        require_token()
        payload = request.get_json(force=True) or {}
        engine.set_mode(str(payload.get("mode", "PAPER")))
        return jsonify({"ok": True, "mode": engine.mode})

    return app
