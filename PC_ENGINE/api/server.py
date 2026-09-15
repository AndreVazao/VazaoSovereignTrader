from __future__ import annotations

from flask import Flask, Response, jsonify, request

from PC_ENGINE.api.dashboard import DASHBOARD_HTML
from PC_ENGINE.core.config import env_value
from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.real_mode_guard import RealModeGuard
from PC_ENGINE.core.real_readiness_service import RealReadinessService


def create_app(engine: SovereignEngine, token_env: str = "VST_LOCAL_TOKEN") -> Flask:
    app = Flask(__name__)
    readiness = RealReadinessService(engine.config)
    guard = RealModeGuard(engine.config.get("real_mode_guard", {}))

    def require_token() -> None:
        expected = env_value(token_env, "change-this-local-token")
        provided = request.headers.get("X-Token", "")
        if expected and provided != expected:
            raise PermissionError("unauthorized")

    @app.errorhandler(PermissionError)
    def handle_unauthorized(_: PermissionError):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    @app.get("/")
    @app.get("/dashboard")
    def dashboard():
        return Response(DASHBOARD_HTML, mimetype="text/html")

    @app.get("/status")
    def status():
        require_token()
        payload = engine.snapshot()
        payload["real_mode_guard"] = guard.snapshot()
        return jsonify(payload)

    @app.get("/readiness")
    @app.get("/real-readiness")
    def real_readiness():
        require_token()
        return jsonify(readiness.collect(engine))

    @app.post("/real/arm")
    def real_arm():
        require_token()
        payload = request.get_json(force=True) or {}
        phrase = str(payload.get("phrase", ""))
        ok, reason = guard.arm(phrase)
        return jsonify({"ok": ok, "reason": reason, "guard": guard.snapshot()}), (200 if ok else 403)

    @app.post("/real/disarm")
    def real_disarm():
        require_token()
        guard.disarm("operator disarmed")
        return jsonify({"ok": True, "guard": guard.snapshot()})

    @app.post("/preflight")
    def preflight():
        require_token()
        return jsonify(engine.run_preflight())

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
        guard.disarm("engine stopped")
        return jsonify({"ok": True})

    @app.post("/mode")
    def mode():
        require_token()
        payload = request.get_json(force=True) or {}
        requested = str(payload.get("mode", "PAPER")).upper()

        if requested == "REAL":
            report = readiness.collect(engine)
            if not report.get("ready", False):
                return jsonify({
                    "ok": False,
                    "error": "real_readiness_blocked",
                    "readiness": report,
                    "guard": guard.snapshot(),
                }), 409
            authorized, reason = guard.consume()
            if not authorized:
                return jsonify({
                    "ok": False,
                    "error": "real_mode_not_authorized",
                    "reason": reason,
                    "guard": guard.snapshot(),
                }), 403

        if requested == "PAPER":
            guard.disarm("switched to PAPER")

        try:
            engine.set_mode(requested)
        except (ValueError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        return jsonify({"ok": True, "mode": engine.mode, "guard": guard.snapshot()})

    return app
