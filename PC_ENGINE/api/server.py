from __future__ import annotations

from dataclasses import asdict

import hmac
import base64

from flask import Flask, Response, jsonify, request, send_file

from PC_ENGINE.api.dashboard import DASHBOARD_HTML
from PC_ENGINE.core.config import env_value
from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.real_mode_guard import RealModeGuard
from PC_ENGINE.core.real_readiness_service import RealReadinessService
from PC_ENGINE.tools.run_readiness_pipeline import run as run_readiness_pipeline
from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge
from PC_ENGINE.human_bridge.watchdog import HumanBridgeWatchdog
from PC_ENGINE.autonomy.paper_reconciliation import PaperAutonomyReconciler
from PC_ENGINE.research.inbox import TraderResearchInbox


def create_app(engine: SovereignEngine, token_env: str = "VST_LOCAL_TOKEN") -> Flask:
    app = Flask(__name__)
    readiness = RealReadinessService(engine.config)
    guard = RealModeGuard(engine.config.get("real_mode_guard", {}))
    human_cfg = engine.config.get("human_bridge", {})
    human_bridge = getattr(engine, "human_bridge", None)
    human_watchdog = getattr(engine, "human_bridge_watchdog", None)
    if human_bridge is None or human_watchdog is None:
        human_bridge = HumanInteractionBridge(
            human_cfg.get("data_dir", "PC_ENGINE/data/human_bridge"),
            default_ttl_seconds=int(human_cfg.get("human_interaction_ttl_seconds", human_cfg.get("response_timeout_seconds", 900))),
        )
        human_watchdog = HumanBridgeWatchdog(human_bridge, human_cfg)
    research = TraderResearchInbox(engine.config.get("research", {}).get("data_dir", "PC_ENGINE/data/research"))

    def require_token() -> None:
        expected = env_value(token_env, "")
        provided = request.headers.get("X-Token", "")
        if not expected or not hmac.compare_digest(provided, expected):
            raise PermissionError("unauthorized")
        human_watchdog.heartbeat("pc")

    @app.errorhandler(PermissionError)
    def handle_unauthorized(_: PermissionError):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    @app.get("/")
    @app.get("/dashboard")
    def dashboard():
        return Response(DASHBOARD_HTML, mimetype="text/html")

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "service": "VazaoSovereignTrader", "mode": engine.mode})

    @app.get("/status")
    def status():
        require_token()
        if hasattr(engine, "refresh_human_bridge_operational_state"):
            engine.refresh_human_bridge_operational_state()
        payload = engine.snapshot()
        payload["real_mode_guard"] = guard.snapshot()
        return jsonify(payload)

    @app.get("/paper-reconciliation")
    def paper_reconciliation():
        require_token()
        paper_cfg = engine.config.get("paper", {})
        report = PaperAutonomyReconciler(
            intents_path=paper_cfg.get("autonomous_intents_path", "PC_ENGINE/data/paper/autonomous_intents.jsonl"),
            fills_path=paper_cfg.get("fills_path", "PC_ENGINE/data/paper/fills.jsonl"),
            runs_path=paper_cfg.get("runs_path", "PC_ENGINE/data/paper/runs.jsonl"),
            output_path=paper_cfg.get("reconciliation_path", "PC_ENGINE/data/paper/autonomous_reconciliation.json"),
        ).reconcile()
        return jsonify(report)

    @app.get("/readiness")
    @app.get("/real-readiness")
    def real_readiness():
        require_token()
        return jsonify(readiness.collect(engine))

    @app.post("/readiness/run")
    def readiness_run():
        require_token()
        if engine.mode.upper() != "PAPER":
            return jsonify({"ok": False, "error": "readiness_pipeline_requires_paper_mode"}), 409
        try:
            result = run_readiness_pipeline(engine.config.get("real_readiness", {}).get("data_dir", "PC_ENGINE/data/radar"))
        except Exception as exc:
            return jsonify({"ok": False, "error": f"readiness_pipeline_failed: {exc}"}), 500
        return jsonify({"ok": True, "result": result, "readiness": readiness.collect(engine)})

    @app.get("/research")
    def research_snapshot():
        require_token()
        return jsonify(research.snapshot())

    @app.post("/research")
    def research_submit():
        require_token()
        payload = request.get_json(force=True) or {}
        try:
            item = research.submit(str(payload.get("message", "")))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "request": asdict(item)})

    @app.post("/human-interaction/heartbeat")
    def human_interaction_heartbeat():
        require_token()
        source = str((request.get_json(force=True) or {}).get("source", "mobile")).lower()
        try:
            human_watchdog.heartbeat(source)
            return jsonify({"ok": True, "watchdog": engine.refresh_human_bridge_operational_state()})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/human-interaction/watchdog")
    def human_interaction_watchdog():
        require_token()
        return jsonify(engine.refresh_human_bridge_operational_state())
    @app.get("/human-interaction/pending")
    def human_interaction_pending():
        require_token()
        return jsonify(human_bridge.snapshot())

    @app.post("/human-interaction/request")
    def human_interaction_request():
        require_token()
        payload = request.get_json(force=True) or {}
        item = human_bridge.create_request(
            str(payload.get("platform", "browser")),
            str(payload.get("kind", "CUSTOM")),
            str(payload.get("title", "Intervenção necessária")),
            str(payload.get("message", "")),
            url=payload.get("url"),
            screenshot_path=payload.get("screenshot_path"),
            fields=payload.get("fields") or [],
        )
        return jsonify({"ok": True, "request": human_bridge.public_item(item)})

    @app.get("/human-interaction/screenshot-data/<request_id>")
    def human_interaction_screenshot_data(request_id: str):
        require_token()
        item = next((x for x in human_bridge.pending() if x.get("request_id") == request_id), None)
        if not item or not item.get("screenshot_path"):
            return jsonify({"ok": False, "error": "screenshot_not_available"}), 404
        try:
            with open(item["screenshot_path"], "rb") as handle:
                encoded = base64.b64encode(handle.read()).decode("ascii")
            return jsonify({"ok": True, "mime": "image/png", "data": encoded})
        except (OSError, ValueError):
            return jsonify({"ok": False, "error": "screenshot_unavailable"}), 404

    @app.post("/human-interaction/browser-action")
    def human_interaction_browser_action():
        require_token()
        payload = request.get_json(force=True) or {}
        request_id = str(payload.get("request_id", ""))
        # The browser connector consumes the RAM-only response and reproduces the action locally.
        ok = human_bridge.respond(request_id, action=str(payload.get("action", "click")), values=payload.get("values") or {}, claim_token=str(payload.get("claim_token", "")))
        return jsonify({"ok": ok}), (200 if ok else 404)

    @app.post("/human-interaction/reissue-claim")
    def human_interaction_reissue_claim():
        require_token()
        request_id = str((request.get_json(force=True) or {}).get("request_id", ""))
        token = human_bridge.reissue_claim(request_id)
        if not token:
            return jsonify({"ok": False, "error": "claim_reissue_not_allowed"}), 409
        item = human_bridge.get(request_id)
        return jsonify({"ok": True, "request": human_bridge.public_item(item)})

    @app.post("/human-interaction/respond")
    def human_interaction_respond():
        require_token()
        payload = request.get_json(force=True) or {}
        request_id = str(payload.get("request_id", ""))
        values = payload.get("values") or {}
        claim_token = str(payload.get("claim_token", ""))
        if not isinstance(values, dict):
            return jsonify({"ok": False, "error": "values_must_be_object"}), 400
        ok = human_bridge.respond(request_id, action=str(payload.get("action", "fill")), values=values, claim_token=claim_token)
        return jsonify({"ok": ok}), (200 if ok else 404)

    @app.post("/human-interaction/cancel")
    def human_interaction_cancel():
        require_token()
        request_id = str((request.get_json(force=True) or {}).get("request_id", ""))
        ok = human_bridge.cancel(request_id)
        return jsonify({"ok": ok}), (200 if ok else 404)

    @app.get("/human-interaction/status/<request_id>")
    def human_interaction_status(request_id: str):
        require_token()
        item = next((x for x in human_bridge.snapshot().get("requests", []) if x.get("request_id") == request_id), None)
        return jsonify({"ok": item is not None, "request": item}), (200 if item else 404)

    @app.get("/human-interaction/screenshot/<request_id>")
    def human_interaction_screenshot(request_id: str):
        require_token()
        item = next((x for x in human_bridge.pending() if x.get("request_id") == request_id), None)
        if not item or not item.get("screenshot_path"):
            return jsonify({"ok": False, "error": "screenshot_not_available"}), 404
        path = item["screenshot_path"]
        try:
            return send_file(path, mimetype="image/png", max_age=0)
        except (OSError, ValueError):
            return jsonify({"ok": False, "error": "screenshot_unavailable"}), 404

    @app.post("/real/arm")
    def real_arm():
        require_token()
        payload = request.get_json(force=True) or {}
        ok, reason = guard.arm(str(payload.get("phrase", "")))
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
        if engine.mode.upper() == "REAL":
            if engine.state.pending_orders:
                return jsonify({"ok": False, "error": "real_start_requires_pending_order_reconciliation", "orders": list(engine.state.pending_orders)}), 409
            reconciliation = engine.reconcile_account_state()
            if not reconciliation.get("ok", False):
                return jsonify({"ok": False, "error": "real_account_reconciliation_blocked", "reconciliation": reconciliation}), 409
            report = readiness.collect(engine)
            if not report.get("ready", False):
                return jsonify({"ok": False, "error": "real_readiness_blocked", "readiness": report}), 409
            authorized, reason = guard.consume()
            if not authorized:
                return jsonify({"ok": False, "error": "real_start_not_authorized", "reason": reason, "guard": guard.snapshot()}), 403
        engine.start()
        return jsonify({"ok": True, "mode": engine.mode})

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
            if engine.state.open_positions:
                return jsonify({"ok": False, "error": "real_mode_requires_manual_position_reconciliation", "positions": list(engine.state.open_positions)}), 409
            if engine.state.pending_orders:
                return jsonify({"ok": False, "error": "real_mode_requires_pending_order_reconciliation", "orders": list(engine.state.pending_orders)}), 409
            authorized, reason = guard.can_enable_real()
            if not authorized:
                return jsonify({"ok": False, "error": "real_mode_not_authorized", "reason": reason, "guard": guard.snapshot()}), 403
            engine.set_mode("REAL")
            preflight = engine.run_preflight()
            reconciliation = engine.reconcile_account_state()
            report = readiness.collect(engine)
            if not preflight.get("ok") or not reconciliation.get("ok", False) or not report.get("ready", False):
                engine.set_mode("PAPER")
                guard.disarm("REAL readiness failed; authorization revoked")
                return jsonify({
                    "ok": False,
                    "error": "real_readiness_blocked",
                    "preflight": preflight,
                    "readiness": report,
                    "reconciliation": reconciliation,
                    "guard": guard.snapshot(),
                }), 409
            return jsonify({"ok": True, "mode": engine.mode, "guard": guard.snapshot(), "readiness": report})

        if requested == "PAPER":
            guard.disarm("switched to PAPER")

        try:
            engine.set_mode(requested)
        except (ValueError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409
        return jsonify({"ok": True, "mode": engine.mode, "guard": guard.snapshot()})

    return app
