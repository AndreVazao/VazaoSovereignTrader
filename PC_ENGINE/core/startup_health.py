# Path: PC_ENGINE/core/startup_health.py
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PC_ENGINE.core.recovery import RecoveryManager


class StartupHealth:
    """Deterministic local startup verification; never enables REAL."""

    def __init__(self, data_dir: str | Path, config: dict[str, Any]):
        self.data_dir = Path(data_dir)
        self.config = config if isinstance(config, dict) else {}
        self.path = self.data_dir / "startup_health.json"

    def run(self, recovery: "RecoveryManager | None" = None) -> dict[str, Any]:
        checks: dict[str, Any] = {}
        self.data_dir.mkdir(parents=True, exist_ok=True)
        checks["data_dir"] = {"ok": self.data_dir.is_dir(), "path": str(self.data_dir)}

        config_mode = str(self.config.get("mode", "PAPER")).upper()
        checks["startup_mode"] = {
            "ok": config_mode != "REAL",
            "configured": config_mode,
            "effective": "PAPER" if config_mode == "REAL" else config_mode,
        }

        if recovery is not None:
            recovery_diag = recovery.diagnostics()
            checks["recovery_integrity"] = {
                "ok": bool(recovery_diag.get("integrity_ok", True)),
                "source": recovery_diag.get("recovery_source"),
                "generation": recovery_diag.get("generation", 0),
                "primary_valid": recovery_diag.get("primary_valid"),
                "backup_valid": recovery_diag.get("backup_valid"),
            }
        else:
            checks["recovery_integrity"] = {
                "ok": False,
                "reason": "recovery_manager_missing",
            }

        critical = [
            name
            for name, value in checks.items()
            if isinstance(value, dict) and value.get("ok") is False
        ]
        report = {
            "schema_version": 1,
            "timestamp": int(time.time()),
            "status": "READY" if not critical else "SAFE_STATE",
            "paper_only": True,
            "real_promotion_attempted": False,
            "critical_checks": critical,
            "checks": checks,
        }

        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)
        return report
