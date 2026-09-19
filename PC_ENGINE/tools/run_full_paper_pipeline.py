from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run(module: str, args: list[str] | None = None) -> dict:
    command = [sys.executable, "-m", module, *(args or [])]
    started = time.time()
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return {
        "module": module,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _exists(path: str) -> bool:
    return (ROOT / path).exists()


def run() -> dict:
    """Run the deterministic PAPER evidence chain.

    Continuous market collection is deliberately not hidden inside this command:
    collection is a long-running service. This pipeline consumes its evidence and
    fails closed when required artifacts are missing.
    """
    stages: list[dict] = []

    required_collection = [
        "PC_ENGINE/data/radar/websocket_events.jsonl",
        "PC_ENGINE/data/radar/websocket_orderbook_events.jsonl",
    ]
    missing = [path for path in required_collection if not _exists(path)]
    stages.append({
        "stage": "COLLECTION",
        "ok": not missing,
        "required_artifacts": required_collection,
        "missing": missing,
        "note": "Run the continuous market and L2 collectors until sufficient evidence exists." if missing else "Collection artifacts present.",
    })
    if missing:
        report = {"pipeline": "PAPER_TO_REAL_READINESS", "status": "BLOCKED", "stages": stages}
        _write(report)
        return report

    for module, args, name in [
        ("PC_ENGINE.tools.run_readiness_pipeline", [], "VALIDATION"),
        ("PC_ENGINE.tools.run_l2_temporal_replay", [], "L2_REPLAY"),
        ("PC_ENGINE.tools.run_l2_oos_validation", [], "OOS_VALIDATION"),
        ("PC_ENGINE.tools.run_paper_autonomy", [], "GOD_PAPER"),
        ("PC_ENGINE.tools.run_paper_reconciliation", [], "RECONCILIATION"),
    ]:
        result = _run(module, args)
        result["stage"] = name
        stages.append(result)
        if not result["ok"]:
            report = {"pipeline": "PAPER_TO_REAL_READINESS", "status": "BLOCKED", "stages": stages}
            _write(report)
            return report

    readiness = _read_json(ROOT / "PC_ENGINE/data/radar/real_readiness.json")
    reconciliation = _read_json(ROOT / "PC_ENGINE/data/paper/autonomous_reconciliation.json")
    final = {
        "pipeline": "PAPER_TO_REAL_READINESS",
        "status": "READY_FOR_PROTECTED_REAL_REVIEW" if readiness.get("ready") else "LOCKED",
        "stages": stages,
        "readiness": readiness,
        "reconciliation": {
            "status": reconciliation.get("status"),
            "intents": reconciliation.get("intents", 0),
            "reconciled_intents": reconciliation.get("reconciled_intents", 0),
            "missing_intents": reconciliation.get("missing_intents", 0),
            "net_pnl": reconciliation.get("net_pnl", 0.0),
        },
    }
    _write(final)
    return final


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(payload: dict) -> None:
    path = ROOT / "PC_ENGINE/data/paper/full_pipeline_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
