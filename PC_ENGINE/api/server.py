from __future__ import annotations

from dataclasses import asdict

import base64
import json

from flask import Flask, Response, jsonify, request, send_file

from PC_ENGINE.api.dashboard import DASHBOARD_HTML
from PC_ENGINE.core.config import DATA_DIR, env_value
from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.identity import IdentityAuthenticator, AuthenticatedPrincipal
from PC_ENGINE.core.mobile_pairing import MobilePairingStore
from PC_ENGINE.core.real_mode_guard import RealModeGuard
from PC_ENGINE.core.real_readiness_service import RealReadinessService
from PC_ENGINE.tools.run_readiness_pipeline import run as run_readiness_pipeline
from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge
from PC_ENGINE.human_bridge.watchdog import HumanBridgeWatchdog
from PC_ENGINE.autonomy.paper_reconciliation import PaperAutonomyReconciler
from PC_ENGINE.research.inbox import TraderResearchInbox
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
from PC_ENGINE.learning.evidence_learning_loop import PaperEvidenceLearningLoop
from PC_ENGINE.diagnostics.operational import build_operational_diagnostics, latest_events_by_venue_symbol, storage_metrics
from PC_ENGINE.diagnostics.venue_health import build_venue_health
from PC_ENGINE.diagnostics.path_utils import resolve_config_path
from PC_ENGINE.diagnostics.evidence_scorecard import build_runtime_evidence_scorecard, refresh_runtime_evidence_reports
from PC_ENGINE.diagnostics.execution_surface_catalog import build_execution_surface_catalog
from PC_ENGINE.execution.surface_runtime_manager import ExecutionSurfaceRuntimeManager
from PC_ENGINE.api.operator_exchange import OperatorExchange


def create_app(engine: SovereignEngine, token_env: str = "VST_LOCAL_TOKEN") -> Flask:
    app = Flask(__name__)
    readiness = RealReadinessService(engine.config)
    guard_settings = dict(engine.config.get("real_mode_guard", {}))
    guard_settings["allow_real"] = bool(engine.config.get("autonomous_execution", {}).get("allow_real", False))
    guard = RealModeGuard(guard_settings)
    engine.real_mode_guard = guard
    identity = IdentityAuthenticator(engine.config, env_value, fallback_token_env=token_env)
    pairing_cfg = engine.config.get("mobile_pairing", {})
    configured_pairing_dir = pairing_cfg.get("data_dir")
    pairing_dir = resolve_config_path(configured_pairing_dir) if configured_pairing_dir else DATA_DIR / "mobile_pairing"
    mobile_pairing = MobilePairingStore(pairing_dir, owner_id=engine.owner_id)
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
    surface_runtime = ExecutionSurfaceRuntimeManager(engine.config)
    exchange_cfg = dict(engine.config.get("operator_exchange", {}))
    operator_exchange = OperatorExchange(
        exchange_cfg.get("data_dir", "PC_ENGINE/data/operator_exchange"),
        max_upload_mb=int(exchange_cfg.get("max_upload_mb", 25)),
    )

    def require_token() -> AuthenticatedPrincipal:
        provided = request.headers.get("X-Token", "")
        tailscale_identity = request.headers.get("X-Tailscale-Identity", "")
        device_id = request.headers.get("X-Device-ID", "")
        try:
            principal = mobile_pairing.authenticate(provided)
        except RuntimeError:
            # A corrupt pairing registry must fail device auth closed without locking out the owner token.
            principal = None
        if principal is None:
            principal = identity.authenticate(
                provided,
                tailscale_identity=tailscale_identity,
                device_id=device_id,
            )
        if principal.owner_id != engine.owner_id:
            raise PermissionError("owner_mismatch")
        human_watchdog.heartbeat("pc")
        return principal

    def require_scope(scope: str) -> AuthenticatedPrincipal:
        principal = require_token()
        if not principal.has(scope):
            raise PermissionError(f"scope_required:{scope}")
        return principal

    def require_any_scope(*scopes: str) -> AuthenticatedPrincipal:
        principal = require_token()
        if not any(principal.has(scope) for scope in scopes):
            raise PermissionError("scope_required")
        return principal

    @app.errorhandler(PermissionError)
    def handle_unauthorized(_: PermissionError):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    @app.get("/")
    @app.get("/dashboard")
    def dashboard():
        return Response(DASHBOARD_HTML, mimetype="text/html")

    @app.get("/operator-files")
    def operator_files():
        require_scope("read_private_state")
        return jsonify({
            "ok": True,
            "root": str(operator_exchange.root),
            "folders": {
                "INBOX": operator_exchange.list_files("INBOX"),
                "OUTBOX": operator_exchange.list_files("OUTBOX"),
            },
            "upload_folder": "INBOX",
            "paper_only": True,
        })

    @app.post("/operator-files/upload")
    def operator_files_upload():
        require_scope("read_private_state")
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify({"ok": False, "error": "file_required"}), 400
        try:
            result = operator_exchange.save_upload("INBOX", uploaded.filename, uploaded.stream)
            return jsonify({
                "ok": True,
                "file": result,
                "folder": "INBOX",
                "paper_only": True,
                "execution_authorized": False,
            })
        except (OSError, ValueError, PermissionError) as exc:
            return jsonify({"ok": False, "error": "operator_file_upload_failed", "detail": str(exc)}), 400

    @app.get("/operator-files/<folder>/<filename>")
    def operator_file_download(folder: str, filename: str):
        require_scope("read_private_state")
        try:
            path = operator_exchange.resolve_download(folder, filename)
        except (OSError, ValueError, FileNotFoundError) as exc:
            return jsonify({"ok": False, "error": "operator_file_not_found", "detail": str(exc)}), 404
        return send_file(path, as_attachment=True, download_name=path.name)

    @app.get("/health")
    def health():
        return jsonify({
            "ok": True,
            "service": "VazaoSovereignTrader",
            "mode": engine.mode,
            "owner_id": engine.owner_id,
        })

    @app.get("/market-data-health")
    def market_data_health():
        require_scope("read_private_state")
        radar_cfg = engine.config.get("radar", {})
        raw_dir = radar_cfg.get("data_dir", "PC_ENGINE/data/radar")
        health_path = resolve_config_path(raw_dir) / "market_data_health.json"
        if not health_path.exists():
            return jsonify({
                "ok": False,
                "status": "NOT_STARTED",
                "reason": "market_data_health_file_missing",
                "health_path": str(health_path),
            })
        try:
            payload = json.loads(health_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return jsonify({"ok": False, "status": "INVALID", "error": str(exc)}), 409
        now_ms = __import__("time").time_ns() // 1_000_000
        age_ms = max(0, now_ms - int(payload.get("timestamp_ms", now_ms)))
        payload["health_age_ms"] = age_ms
        payload["stale"] = age_ms > int(radar_cfg.get("health_stale_seconds", 30)) * 1000
        payload["ok"] = payload.get("status") == "RUNNING" and not payload["stale"]
        return jsonify(payload)

    @app.get("/diagnostics")
    def operational_diagnostics():
        require_scope("read_private_state")
        from pathlib import Path
        import time
        engine_snapshot = engine.snapshot()
        radar_cfg = engine.config.get("radar", {})
        raw_dir = radar_cfg.get("data_dir", "PC_ENGINE/data/radar")
        raw_path = resolve_config_path(raw_dir)
        health_path = raw_path / "market_data_health.json"
        market_data = {"status": "NOT_STARTED", "ok": False, "stale": True}
        if health_path.exists():
            try:
                market_data = json.loads(health_path.read_text(encoding="utf-8"))
                now_ms = time.time_ns() // 1_000_000
                market_data["health_age_ms"] = max(0, now_ms - int(market_data.get("timestamp_ms", now_ms)))
                market_data["stale"] = market_data["health_age_ms"] > int(radar_cfg.get("health_stale_seconds", 30)) * 1000
                market_data["ok"] = market_data.get("status") == "RUNNING" and not market_data["stale"]
            except (OSError, ValueError, TypeError):
                market_data = {"status": "INVALID", "ok": False, "stale": True}
        event_path = raw_path / "websocket_events.jsonl"
        data_root = raw_path.parent
        state_path = data_root / "operational_diagnostics_state.json"
        previous_bytes = None
        try:
            if state_path.exists():
                previous_bytes = int(json.loads(state_path.read_text(encoding="utf-8")).get("bytes"))
        except (OSError, ValueError, TypeError):
            previous_bytes = None
        storage = storage_metrics(data_root, previous_bytes)
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps({"bytes": storage["bytes"]}, sort_keys=True) + "\n", encoding="utf-8")
        except OSError:
            pass
        return jsonify(build_operational_diagnostics(
            engine=engine_snapshot,
            market_data=market_data,
            latest_events=latest_events_by_venue_symbol(event_path),
            storage=storage,
            recovery=getattr(getattr(engine, "recovery", None), "diagnostics", lambda: {})(),
        ))

    @app.post("/evidence-scorecard/refresh")
    def evidence_scorecard_refresh():
        require_scope("read_private_state")
        try:
            return jsonify(refresh_runtime_evidence_reports(engine.config))
        except (OSError, ValueError, TypeError) as exc:
            return jsonify({
                "ok": False,
                "error": "evidence_refresh_failed",
                "detail": str(exc),
                "paper_only": True,
                "orders_submitted": False,
                "execution_authorized": False,
            }), 409

    @app.get("/evidence-scorecard")
    def evidence_scorecard():
        require_scope("read_private_state")
        return jsonify(build_runtime_evidence_scorecard(engine.config))

    @app.get("/execution-surfaces")
    def execution_surfaces():
        require_scope("read_private_state")
        return jsonify(build_execution_surface_catalog(engine.config, runtime_snapshot=surface_runtime.snapshot()))

    @app.get("/execution-surfaces/runtime")
    def execution_surfaces_runtime():
        require_scope("read_private_state")
        return jsonify(surface_runtime.snapshot())

    @app.post("/execution-surfaces/runtime/instantiate")
    def execution_surfaces_runtime_instantiate():
        require_scope("trade_paper")
        payload = request.get_json(silent=True) or {}
        try:
            from PC_ENGINE.execution.surface_adapters import Surface
            surface = Surface(str(payload.get("surface", "")).strip().upper())
            result = surface_runtime.instantiate(
                runtime_id=str(payload.get("runtime_id", "")),
                venue_id=str(payload.get("venue_id", "")),
                surface=surface,
            )
            return jsonify({"ok": True, "record": result, "paper_only": True, "orders_submitted": False, "execution_authorized": False})
        except (KeyError, ValueError, TypeError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": "runtime_instantiate_failed", "detail": str(exc)}), 400

    @app.post("/execution-surfaces/runtime/probe")
    def execution_surfaces_runtime_probe():
        require_scope("trade_paper")
        payload = request.get_json(silent=True) or {}
        try:
            result = surface_runtime.probe(str(payload.get("runtime_id", "")))
            return jsonify({"ok": True, "feedback": result, "paper_only": True, "orders_submitted": False, "execution_authorized": False})
        except (KeyError, ValueError, TypeError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": "runtime_probe_failed", "detail": str(exc)}), 400

    @app.post("/execution-surfaces/runtime/close")
    def execution_surfaces_runtime_close():
        require_scope("trade_paper")
        payload = request.get_json(silent=True) or {}
        try:
            result = surface_runtime.close(str(payload.get("runtime_id", "")))
            return jsonify({"ok": True, "runtime": result, "paper_only": True, "orders_submitted": False, "execution_authorized": False})
        except (KeyError, ValueError, TypeError, RuntimeError) as exc:
            return jsonify({"ok": False, "error": "runtime_close_failed", "detail": str(exc)}), 400

    @app.get("/venue-health")
    def venue_health():
        require_scope("read_private_state")
        return jsonify(build_venue_health(engine.config))

    @app.get("/venue-economic-evidence")
    def venue_economic_evidence():
        require_scope("read_private_state")
        radar_cfg = engine.config.get("radar", {})
        report_cfg = radar_cfg.get("evidence_reports", {})
        configured = report_cfg.get("venue_economic_evidence")
        if configured:
            report_path = resolve_config_path(configured)
        else:
            report_path = resolve_config_path(radar_cfg.get("data_dir", "PC_ENGINE/data/radar")) / "venue_economic_evidence.json"
        if not report_path.exists():
            return jsonify({
                "status": "NOT_STARTED",
                "report_path": str(report_path),
                "venues": [],
                "paper_only": True,
                "orders_submitted": False,
                "execution_authorized": False,
            })
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            return jsonify({
                "status": "INVALID",
                "error": "venue_economic_evidence_invalid",
                "paper_only": True,
                "orders_submitted": False,
                "execution_authorized": False,
            }), 409
        if (
            not isinstance(payload, dict)
            or payload.get("paper_only") is not True
            or payload.get("orders_submitted") is not False
            or payload.get("execution_authorized") is not False
            or not isinstance(payload.get("venues"), list)
        ):
            return jsonify({
                "status": "INVALID",
                "error": "venue_economic_evidence_safety_invariant_failed",
                "paper_only": True,
                "orders_submitted": False,
                "execution_authorized": False,
            }), 409
        payload["report_path"] = str(report_path)
        return jsonify(payload)

    @app.get("/diagnostics/export")
    def operational_diagnostics_export():
        require_scope("read_private_state")
        payload = operational_diagnostics().get_json()
        response = Response(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", mimetype="application/json")
        response.headers["Content-Disposition"] = 'attachment; filename="vazao-operational-diagnostics.json"'
        return response

    @app.post("/mobile-pairing/request")
    def mobile_pairing_request():
        principal = require_token()
        if principal.auth_method != "local_token":
            return jsonify({"ok": False, "error": "owner_token_required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            result = mobile_pairing.create_challenge(str(payload.get("device_name", "")))
            return jsonify({"ok": True, **result})
        except (ValueError, RuntimeError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409

    @app.get("/mobile-pairing/status/<challenge_id>")
    def mobile_pairing_status(challenge_id: str):
        principal = require_token()
        if principal.auth_method != "local_token":
            return jsonify({"ok": False, "error": "owner_token_required"}), 403
        try:
            state = mobile_pairing.challenge_status(challenge_id)
            return jsonify({"ok": True, **state})
        except (ValueError, RuntimeError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404

    @app.post("/mobile-pairing/complete")
    def mobile_pairing_complete():
        principal = require_token()
        if principal.auth_method != "local_token":
            return jsonify({"ok": False, "error": "owner_token_required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            result = mobile_pairing.complete(
                str(payload.get("challenge_id", "")),
                str(payload.get("confirmation_code", "")),
            )
            return jsonify({"ok": True, **result})
        except PermissionError:
            return jsonify({"ok": False, "error": "confirmation_code_invalid"}), 403
        except (ValueError, RuntimeError, OSError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409

    @app.get("/mobile-pairing/devices")
    def mobile_pairing_devices():
        principal = require_token()
        if principal.auth_method != "local_token":
            return jsonify({"ok": False, "error": "owner_token_required"}), 403
        try:
            return jsonify({"ok": True, "devices": mobile_pairing.list_devices()})
        except (RuntimeError, OSError) as exc:
            return jsonify({"ok": False, "error": "pairing_store_unavailable"}), 409

    @app.post("/mobile-pairing/revoke")
    def mobile_pairing_revoke():
        principal = require_token()
        if principal.auth_method != "local_token":
            return jsonify({"ok": False, "error": "owner_token_required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify({"ok": True, **mobile_pairing.revoke(str(payload.get("device_id", "")))})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except (RuntimeError, OSError):
            return jsonify({"ok": False, "error": "pairing_store_unavailable"}), 409

    @app.get("/identity")
    def identity_route():
        principal = require_token()
        return jsonify({
            "ok": True,
            "owner": engine.owner_context.snapshot(),
            "principal": principal.snapshot(),
        })

    @app.get("/status")
    def status():
        require_scope("read_private_state")
        if hasattr(engine, "refresh_human_bridge_operational_state"):
            engine.refresh_human_bridge_operational_state()
        payload = engine.snapshot()
        payload["real_mode_guard"] = guard.snapshot()
        return jsonify(payload)

    @app.get("/paper-reconciliation")
    def paper_reconciliation():
        require_scope("read_private_state")
        paper_cfg = engine.config.get("paper", {})
        report = PaperAutonomyReconciler(
            intents_path=paper_cfg.get("autonomous_intents_path", "PC_ENGINE/data/paper/autonomous_intents.jsonl"),
            fills_path=paper_cfg.get("fills_path", "PC_ENGINE/data/paper/fills.jsonl"),
            runs_path=paper_cfg.get("runs_path", "PC_ENGINE/data/paper/runs.jsonl"),
            output_path=paper_cfg.get("reconciliation_path", "PC_ENGINE/data/paper/autonomous_reconciliation.json"),
        ).reconcile()
        return jsonify(report)

    @app.get("/evidence-ledger/audit")
    def evidence_ledger_audit():
        require_scope("read_private_state")
        evidence_cfg = engine.config.get("evidence", {})
        ledger_path = evidence_cfg.get("ledger_path", "PC_ENGINE/data/radar/evidence_ledger.jsonl")
        try:
            records = EvidenceLedger.load(ledger_path)
            report = EvidenceLedger.audit_report(records)
        except (OSError, ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": "evidence_ledger_invalid", "detail": str(exc)}), 409
        return jsonify({
            "ok": True,
            "ledger_path": str(ledger_path),
            "report": asdict(report),
        })

    @app.get("/evidence-ledger")
    def evidence_ledger_snapshot():
        require_scope("read_private_state")
        evidence_cfg = engine.config.get("evidence", {})
        ledger_path = evidence_cfg.get("ledger_path", "PC_ENGINE/data/radar/evidence_ledger.jsonl")
        raw_eligible = request.args.get("eligible")
        eligible = None
        if raw_eligible is not None:
            normalized = raw_eligible.strip().lower()
            if normalized not in {"true", "false"}:
                return jsonify({"ok": False, "error": "eligible_must_be_boolean"}), 400
            eligible = normalized == "true"
        filters = {
            "candidate_id": request.args.get("candidate_id"),
            "version": request.args.get("version"),
            "symbol": request.args.get("symbol"),
            "regime": request.args.get("regime"),
            "eligible": eligible,
        }
        try:
            records = EvidenceLedger.query(ledger_path, **filters)
        except (OSError, ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": "evidence_ledger_invalid", "detail": str(exc)}), 409
        summary = EvidenceLedger.summarize(records)
        return jsonify({
            "ok": True,
            "ledger_path": str(ledger_path),
            "filters": filters,
            "summary": asdict(summary),
            "records": [record.to_dict() for record in records],
        })

    @app.get("/evidence-learning")
    def evidence_learning():
        require_scope("read_private_state")
        evidence_cfg = engine.config.get("evidence", {})
        ledger_path = evidence_cfg.get("ledger_path", "PC_ENGINE/data/radar/evidence_ledger.jsonl")
        learning_cfg = dict(evidence_cfg.get("learning_loop", {}))
        try:
            records = EvidenceLedger.load(ledger_path)
            loop = PaperEvidenceLearningLoop(
                recent_records=int(learning_cfg.get("recent_records", 20)),
                degradation_threshold=float(learning_cfg.get("degradation_threshold", 0.20)),
            )
            snapshot = loop.evaluate(records)
        except (OSError, ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": "evidence_learning_invalid", "detail": str(exc)}), 409
        return jsonify({
            "ok": True,
            "ledger_path": str(ledger_path),
            "paper_only": True,
            "snapshot": snapshot.to_dict(),
        })

    @app.get("/research/status")
    def research_status():
        require_scope("read_private_state")
        from pathlib import Path
        radar_cfg = engine.config.get("radar", {})
        study_cfg = engine.config.get("paper_study", {})
        data_dir = Path(radar_cfg.get("data_dir", "PC_ENGINE/data/radar"))
        report_names = {
            "paper_study": study_cfg.get("report_filename", "paper_study_report.json"),
            "websocket_timing": study_cfg.get("timing_report_filename", "websocket_timing_validation.json"),
        }
        reports = {}
        now_ms = __import__("time").time_ns() // 1_000_000
        for name, filename in report_names.items():
            path = data_dir / str(filename)
            if not path.exists():
                reports[name] = {"status": "NOT_STARTED", "path": str(path)}
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                modified_ms = int(path.stat().st_mtime_ns // 1_000_000)
                reports[name] = {
                    "status": "READY",
                    "path": str(path),
                    "age_ms": max(0, now_ms - modified_ms),
                    "payload": payload,
                }
            except (OSError, ValueError) as exc:
                reports[name] = {"status": "INVALID", "path": str(path), "error": str(exc)}
        return jsonify({
            "ok": True,
            "paper_only": True,
            "study_enabled": bool(study_cfg.get("enabled", True)),
            "study_interval_minutes": float(study_cfg.get("interval_minutes", 15)),
            "reports": reports,
        })

    @app.get("/readiness/history")
    def readiness_history():
        require_scope("read_private_state")
        return jsonify(readiness.history())

    @app.get("/readiness/trend")
    def readiness_trend():
        require_scope("read_private_state")
        return jsonify(readiness.trend())

    @app.get("/readiness/scorecard")
    def readiness_scorecard():
        require_scope("read_private_state")
        return jsonify(readiness.scorecard())

    @app.get("/readiness/timeline")
    def readiness_timeline():
        require_scope("read_private_state")
        raw_limit = request.args.get("limit")
        limit = None
        if raw_limit is not None:
            try:
                limit = max(1, int(raw_limit))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "limit_must_be_integer"}), 400
        return jsonify(readiness.timeline(
            component=request.args.get("component"),
            direction=request.args.get("direction"),
            from_status=request.args.get("from_status"),
            to_status=request.args.get("to_status"),
            limit=limit,
        ))

    @app.get("/readiness")
    @app.get("/real-readiness")
    def real_readiness():
        require_scope("read_private_state")
        return jsonify(readiness.collect(engine))

    @app.get("/autonomous-readiness")
    def autonomous_readiness():
        """Read-only preview of the REAL promotion gates; never arms or changes mode."""
        require_scope("read_private_state")
        auto_cfg = engine.config.get("autonomous_execution", {})
        try:
            report = readiness.collect(
                engine,
                persist_history=False,
                target_mode="REAL",
            )
        except Exception as exc:
            return jsonify({
                "ok": False,
                "mode": engine.mode,
                "autonomous_enabled": bool(auto_cfg.get("enabled", False)),
                "auto_promote_real": bool(auto_cfg.get("auto_promote_real", False)),
                "allow_real": bool(auto_cfg.get("allow_real", False)),
                "error": "readiness_evaluation_failed",
                "detail": str(exc),
                "promotion_attempted": False,
            }), 503
        return jsonify({
            "ok": True,
            "mode": engine.mode,
            "target_mode": "REAL",
            "autonomous_enabled": bool(auto_cfg.get("enabled", False)),
            "auto_promote_real": bool(auto_cfg.get("auto_promote_real", False)),
            "allow_real": bool(auto_cfg.get("allow_real", False)),
            "promotion_attempted": False,
            "readiness": report,
            "paper_only": engine.mode.upper() == "PAPER",
        })

    @app.post("/readiness/run")
    def readiness_run():
        require_scope("trade_paper")
        if engine.mode.upper() != "PAPER":
            return jsonify({"ok": False, "error": "readiness_pipeline_requires_paper_mode"}), 409
        try:
            result = run_readiness_pipeline(engine.config.get("real_readiness", {}).get("data_dir", "PC_ENGINE/data/radar"))
        except Exception as exc:
            return jsonify({"ok": False, "error": f"readiness_pipeline_failed: {exc}"}), 500
        return jsonify({"ok": True, "result": result, "readiness": readiness.collect(engine)})

    @app.get("/research")
    def research_snapshot():
        require_scope("read_private_state")
        return jsonify(research.snapshot())

    @app.post("/research")
    def research_submit():
        require_scope("publish_shared_intelligence")
        payload = request.get_json(force=True) or {}
        try:
            item = research.submit(str(payload.get("message", "")))
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "request": asdict(item)})

    @app.post("/human-interaction/heartbeat")
    def human_interaction_heartbeat():
        require_scope("read_private_state")
        source = str((request.get_json(force=True) or {}).get("source", "mobile")).lower()
        try:
            human_watchdog.heartbeat(source)
            return jsonify({"ok": True, "watchdog": engine.refresh_human_bridge_operational_state()})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/human-interaction/watchdog")
    def human_interaction_watchdog():
        require_scope("read_private_state")
        return jsonify(engine.refresh_human_bridge_operational_state())

    @app.get("/human-interaction/pending")
    def human_interaction_pending():
        require_scope("read_private_state")
        return jsonify(human_bridge.snapshot())

    @app.post("/human-interaction/request")
    def human_interaction_request():
        require_scope("manage_owner_settings")
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
        require_scope("read_private_state")
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
        require_scope("manage_owner_settings")
        payload = request.get_json(force=True) or {}
        request_id = str(payload.get("request_id", ""))
        ok = human_bridge.respond(request_id, action=str(payload.get("action", "click")), values=payload.get("values") or {}, claim_token=str(payload.get("claim_token", "")))
        return jsonify({"ok": ok}), (200 if ok else 404)

    @app.post("/human-interaction/reissue-claim")
    def human_interaction_reissue_claim():
        require_scope("manage_owner_settings")
        request_id = str((request.get_json(force=True) or {}).get("request_id", ""))
        token = human_bridge.reissue_claim(request_id)
        if not token:
            return jsonify({"ok": False, "error": "claim_reissue_not_allowed"}), 409
        item = human_bridge.get(request_id)
        return jsonify({"ok": True, "request": human_bridge.public_item(item)})

    @app.post("/human-interaction/respond")
    def human_interaction_respond():
        require_any_scope("manage_owner_settings", "respond_human_interaction")
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
        require_any_scope("manage_owner_settings", "respond_human_interaction")
        request_id = str((request.get_json(force=True) or {}).get("request_id", ""))
        ok = human_bridge.cancel(request_id)
        return jsonify({"ok": ok}), (200 if ok else 404)

    @app.get("/human-interaction/status/<request_id>")
    def human_interaction_status(request_id: str):
        require_scope("read_private_state")
        item = next((x for x in human_bridge.snapshot().get("requests", []) if x.get("request_id") == request_id), None)
        return jsonify({"ok": item is not None, "request": item}), (200 if item else 404)

    @app.get("/human-interaction/screenshot/<request_id>")
    def human_interaction_screenshot(request_id: str):
        require_scope("read_private_state")
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
        require_scope("trade_real")
        payload = request.get_json(force=True) or {}
        ok, reason = guard.arm(str(payload.get("phrase", "")))
        return jsonify({"ok": ok, "reason": reason, "guard": guard.snapshot()}), (200 if ok else 403)

    @app.post("/real/disarm")
    def real_disarm():
        require_scope("trade_real")
        guard.disarm("operator disarmed")
        if engine.mode.upper() == "REAL":
            engine.fail_safe_real("operator_disarmed")
        return jsonify({"ok": True, "mode": engine.mode, "guard": guard.snapshot()})

    @app.post("/preflight")
    def preflight():
        require_scope("trade_paper")
        return jsonify(engine.run_preflight())

    @app.post("/safe-mode/recover")
    def recover_safe_mode():
        require_scope("trade_paper")
        payload = request.get_json(force=True) or {}
        result = engine.recover_from_safe_mode(
            human_confirmation=str(payload.get("confirmation", "")),
        )
        return jsonify(result), (200 if result.get("ok") else 409)

    @app.post("/start")
    def start():
        principal = require_scope("trade_paper")
        if engine.mode.upper() == "REAL":
            if not principal.has("trade_real"):
                raise PermissionError("scope_required:trade_real")
            if engine.state.pending_orders:
                return jsonify({"ok": False, "error": "real_start_requires_pending_order_reconciliation", "orders": list(engine.state.pending_orders)}), 409
            reconciliation = engine.reconcile_account_state()
            if not reconciliation.get("ok", False):
                engine.fail_safe_real("account_reconciliation_failed", reconciliation)
                return jsonify({"ok": False, "error": "real_account_reconciliation_blocked", "reconciliation": reconciliation}), 409
            report = readiness.collect(engine)
            paper_review_ready = bool(report.get("paper_review", {}).get("ready", False))
            if not report.get("ready", False) or not paper_review_ready:
                engine.fail_safe_real("real_readiness_failed", {
                    "blockers": report.get("blockers", []),
                    "paper_review_ready": paper_review_ready,
                    "paper_review_blockers": report.get("paper_review", {}).get("blockers", []),
                })
                return jsonify({"ok": False, "error": "real_readiness_blocked", "readiness": report}), 409
            authorized, reason = guard.consume()
            if not authorized:
                return jsonify({"ok": False, "error": "real_start_not_authorized", "reason": reason, "guard": guard.snapshot()}), 403
        engine.start()
        return jsonify({"ok": True, "mode": engine.mode})

    @app.post("/pause")
    def pause():
        require_scope("trade_paper")
        engine.pause(True)
        return jsonify({"ok": True})

    @app.post("/resume")
    def resume():
        require_scope("trade_paper")
        resumed = engine.pause(False)
        if not resumed:
            return jsonify({"ok": False, "error": "safe_mode_requires_explicit_recovery"}), 409
        return jsonify({"ok": True})

    @app.post("/stop")
    def stop():
        require_scope("trade_paper")
        guard.disarm("engine stopped")
        engine.stop()
        return jsonify({"ok": True})

    @app.post("/mode")
    def mode():
        principal = require_scope("trade_paper")
        payload = request.get_json(force=True) or {}
        requested = str(payload.get("mode", "PAPER")).upper()

        if requested == "REAL":
            if not principal.has("trade_real"):
                raise PermissionError("scope_required:trade_real")
            if engine.state.open_positions:
                return jsonify({"ok": False, "error": "real_mode_requires_manual_position_reconciliation", "positions": list(engine.state.open_positions)}), 409
            if engine.state.pending_orders:
                return jsonify({"ok": False, "error": "real_mode_requires_pending_order_reconciliation", "orders": list(engine.state.pending_orders)}), 409
            authorized, reason = guard.can_enable_real()
            if not authorized:
                return jsonify({"ok": False, "error": "real_mode_not_authorized", "reason": reason, "guard": guard.snapshot()}), 403
            engine.set_mode("REAL", real_authorized=True)
            preflight = engine.run_preflight()
            reconciliation = engine.reconcile_account_state()
            report = readiness.collect(engine)
            paper_review_ready = bool(report.get("paper_review", {}).get("ready", False))
            if (
                not preflight.get("ok")
                or not reconciliation.get("ok", False)
                or not report.get("ready", False)
                or not paper_review_ready
            ):
                engine.fail_safe_real("real_readiness_blocked", {
                    "preflight_ok": preflight.get("ok"),
                    "reconciliation_ok": reconciliation.get("ok", False),
                    "readiness_ready": report.get("ready", False),
                    "paper_review_ready": paper_review_ready,
                    "paper_review_blockers": report.get("paper_review", {}).get("blockers", []),
                })
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