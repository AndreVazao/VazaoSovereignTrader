from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from PC_ENGINE.core.config import DATA_DIR


class RecoveryManager:
    def __init__(self, state_path: Path | None = None):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state_path = state_path or (DATA_DIR / "runtime_state.json")

    def save_positions(self, positions: Dict, pending_orders: Dict | None = None, order_guards: Dict[str, float] | None = None, execution_intents: Dict[str, dict] | None = None) -> None:
        payload = {
            "ts": int(time.time()),
            "positions": {symbol: asdict(position) for symbol, position in positions.items()},
            "pending_orders": dict(pending_orders or {}),
            "order_guards": {str(key): float(value) for key, value in (order_guards or {}).items()},
            "execution_intents": dict(execution_intents or {}),
        }
        tmp_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self.state_path)

    def load_state(self) -> Dict:
        if not self.state_path.exists():
            return {"positions": {}, "pending_orders": {}, "order_guards": {}, "execution_intents": {}}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            return {
                "positions": payload.get("positions", {}) if isinstance(payload, dict) else {},
                "pending_orders": payload.get("pending_orders", {}) if isinstance(payload, dict) else {},
                "order_guards": payload.get("order_guards", {}) if isinstance(payload, dict) else {},
                "execution_intents": payload.get("execution_intents", {}) if isinstance(payload, dict) else {},
            }
        except Exception:
            return {"positions": {}, "pending_orders": {}}

    def load_positions(self) -> Dict:
        return self.load_state().get("positions", {})

    def load_pending_orders(self) -> Dict:
        return self.load_state().get("pending_orders", {})

    def load_order_guards(self) -> Dict[str, float]:
        return self.load_state().get("order_guards", {})

    def load_execution_intents(self) -> Dict[str, dict]:
        return self.load_state().get("execution_intents", {})

    def clear(self) -> None:
        if self.state_path.exists():
            self.state_path.unlink()
