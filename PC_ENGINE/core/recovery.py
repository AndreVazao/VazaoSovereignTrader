from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from PC_ENGINE.core.config import DATA_DIR


SCHEMA_VERSION = 2
JOURNAL_SCHEMA_VERSION = 1


def _canonical_payload(payload: dict) -> bytes:
    body = dict(payload)
    body.pop("integrity_sha256", None)
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload: dict) -> str:
    return hashlib.sha256(_canonical_payload(payload)).hexdigest()


class RecoveryConcurrencyError(RuntimeError):
    """Raised when a recovery transaction would conflict with another pending writer."""


class RecoveryManager:
    def __init__(self, state_path: Path | None = None, owner_id: str = "andre"):
        if state_path is None:
            private_dir = DATA_DIR / "owners" / str(owner_id).strip().lower()
            private_dir.mkdir(parents=True, exist_ok=True)
            state_path = private_dir / "runtime_state.json"
        else:
            state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path = state_path
        self.backup_path = state_path.with_suffix(state_path.suffix + ".bak")
        self.reconciliation_journal_path = state_path.with_suffix(state_path.suffix + ".reconciliation.json")

    @staticmethod
    def _empty_state() -> Dict:
        return {
            "positions": {},
            "pending_orders": {},
            "order_guards": {},
            "execution_intents": {},
            "financial_account": {},
            "risk_state": {},
        }

    def _build_payload(
        self,
        positions: Dict,
        pending_orders: Dict | None,
        order_guards: Dict[str, float] | None,
        execution_intents: Dict[str, dict] | None,
        financial_account: Dict | None,
        risk_state: Dict | None,
        generation: int,
    ) -> dict:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "generation": int(generation),
            "ts": int(time.time()),
            "positions": {str(symbol): asdict(position) for symbol, position in sorted(positions.items())},
            "pending_orders": dict(sorted((pending_orders or {}).items())),
            "order_guards": {str(key): float(value) for key, value in sorted((order_guards or {}).items())},
            "execution_intents": dict(sorted((execution_intents or {}).items())),
            "financial_account": dict(financial_account or {}),
            "risk_state": dict(risk_state or {}),
        }
        payload["integrity_sha256"] = _digest(payload)
        return payload

    def _read_valid(self, path: Path) -> tuple[dict | None, str | None]:
        if not path.exists():
            return None, "missing"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("recovery root must be a JSON object")
            fields = self._empty_state()
            for name in fields:
                value = payload.get(name, {})
                if not isinstance(value, dict):
                    raise ValueError(f"recovery field '{name}' must be an object")
            stored_digest = str(payload.get("integrity_sha256", "")).strip()
            if stored_digest and stored_digest != _digest(payload):
                raise ValueError("recovery integrity digest mismatch")
            # Files from schema 1 did not carry a digest; accept them for compatibility.
            if stored_digest:
                schema = int(payload.get("schema_version", 1))
                if schema > SCHEMA_VERSION:
                    raise ValueError(f"unsupported recovery schema: {schema}")
            return payload, None
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}"


    @staticmethod
    def _fsync_directory(path: Path) -> None:
        """Durably persist directory-entry changes when the platform supports it."""
        try:
            directory_fd = os.open(str(path), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Directory fsync is unavailable on some platforms, notably Windows.
            # File-level fsync and atomic same-filesystem replacement remain mandatory.
            pass

    def _write_json_atomic(self, path: Path, payload: dict) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with tmp_path.open("r+", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
        self._fsync_directory(path.parent)

    def _create_json_exclusive(self, path: Path, payload: dict) -> None:
        """Create a new JSON file atomically; fail if another writer won the race."""
        body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with path.open("x", encoding="utf-8") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        self._fsync_directory(path.parent)

    def prepare_reconciliation(self, target_state: dict, ledger_records: list[dict] | None = None) -> str:
        """Durably prepare a reconciliation transaction before live state mutation."""
        import uuid
        if self.reconciliation_journal_path.exists():
            raise RecoveryConcurrencyError(
                "reconciliation transaction already pending; recover or clear it before preparing another"
            )
        current, _ = self._read_valid(self.state_path)
        base_generation = int((current or {}).get("generation", 0) or 0)
        generation = base_generation + 1
        payload = dict(target_state)
        payload["schema_version"] = SCHEMA_VERSION
        payload["generation"] = generation
        payload["ts"] = int(time.time())
        payload["integrity_sha256"] = _digest(payload)
        transaction = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "transaction_id": uuid.uuid4().hex,
            "base_generation": base_generation,
            "target_state": payload,
            "ledger_records": list(ledger_records or []),
        }
        transaction["integrity_sha256"] = _digest(transaction)
        try:
            self._create_json_exclusive(self.reconciliation_journal_path, transaction)
        except FileExistsError as exc:
            raise RecoveryConcurrencyError(
                "reconciliation transaction already pending; recover or clear it before preparing another"
            ) from exc
        return str(transaction["transaction_id"])

    def load_reconciliation_journal(self) -> dict | None:
        path = self.reconciliation_journal_path
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("integrity_sha256") != _digest(payload):
                raise ValueError("reconciliation journal integrity mismatch")
            target = payload.get("target_state")
            if not isinstance(target, dict) or target.get("integrity_sha256") != _digest(target):
                raise ValueError("reconciliation target integrity mismatch")
            if int(payload.get("schema_version", 0)) > JOURNAL_SCHEMA_VERSION:
                raise ValueError("unsupported reconciliation journal schema")
            if not isinstance(payload.get("ledger_records", []), list):
                raise ValueError("reconciliation ledger_records must be a list")
            return payload
        except Exception as exc:
            raise RuntimeError(f"reconciliation journal corrupt: {type(exc).__name__}: {exc}") from exc

    def commit_reconciliation(self, transaction_id: str) -> None:
        journal = self.load_reconciliation_journal()
        if journal is None or str(journal.get("transaction_id")) != str(transaction_id):
            raise RuntimeError("reconciliation transaction missing or mismatched")
        target = dict(journal["target_state"])
        current, current_error = self._read_valid(self.state_path)
        if current is None and current_error not in (None, "missing"):
            # A crash may have left the primary invalid after the backup was
            # durably written. Treat the last valid backup as the recovery
            # baseline and repair the primary from the pending transaction.
            backup, backup_error = self._read_valid(self.backup_path)
            if backup is None:
                raise RecoveryConcurrencyError(
                    f"cannot commit over invalid recovery state: primary={current_error}; backup={backup_error}"
                )
            current = backup
        current_generation = int((current or {}).get("generation", 0) or 0)
        base_generation = int(journal.get("base_generation", max(int(target.get("generation", 1)) - 1, 0)) or 0)
        target_generation = int(target.get("generation", 0) or 0)
        if current_generation == target_generation and current is not None:
            if current.get("integrity_sha256") == target.get("integrity_sha256"):
                return
        if current_generation != base_generation:
            raise RecoveryConcurrencyError(
                f"reconciliation generation conflict: expected {base_generation}, found {current_generation}"
            )
        self._write_json_atomic(self.state_path, target)
        self._write_json_atomic(self.backup_path, target)

    def recover_pending_reconciliation(self, transaction_id: str | None = None) -> str | None:
        """Replay a durable reconciliation after restart, then clear its journal.

        The journal is the recovery intent. If the process crashed after either
        state write but before journal cleanup, replay is safe because commit is
        generation-checked and idempotent for the same target.
        """
        journal = self.load_reconciliation_journal()
        if journal is None:
            return None
        journal_id = str(journal.get("transaction_id"))
        if transaction_id is not None and journal_id != str(transaction_id):
            raise RuntimeError("reconciliation transaction missing or mismatched")
        self.commit_reconciliation(journal_id)
        self.clear_reconciliation()
        return journal_id

    def clear_reconciliation(self) -> None:
        if self.reconciliation_journal_path.exists():
            self.reconciliation_journal_path.unlink()
            self._fsync_directory(self.reconciliation_journal_path.parent)

    def save_positions(
        self,
        positions: Dict,
        pending_orders: Dict | None = None,
        order_guards: Dict[str, float] | None = None,
        execution_intents: Dict[str, dict] | None = None,
        financial_account: Dict | None = None,
        risk_state: Dict | None = None,
    ) -> None:
        current, _ = self._read_valid(self.state_path)
        previous_generation = int((current or {}).get("generation", 0) or 0)
        payload = self._build_payload(
            positions,
            pending_orders,
            order_guards,
            execution_intents,
            financial_account,
            risk_state,
            previous_generation + 1,
        )
        self._write_json_atomic(self.state_path, payload)
        # Keep the last known-good snapshot independently so a damaged primary can recover.
        self._write_json_atomic(self.backup_path, payload)

    def load_state(self) -> Dict:
        primary, primary_error = self._read_valid(self.state_path)
        selected = primary
        recovery_source = "primary"
        recovery_error = None
        if selected is None:
            backup_path = getattr(self, "backup_path", None)
            backup, backup_error = self._read_valid(backup_path) if backup_path is not None else (None, "missing")
            if backup is not None:
                selected = backup
                recovery_source = "backup"
                recovery_error = primary_error
            else:
                recovery_error = f"primary={primary_error}; backup={backup_error}"
        if selected is None:
            state = self._empty_state()
            state["recovery_error"] = recovery_error
            state["recovery_source"] = "none"
            return state

        state = {name: selected.get(name, {}) for name in self._empty_state()}
        state["recovery_source"] = recovery_source
        state["recovery_generation"] = int(selected.get("generation", 0) or 0)
        if recovery_error:
            state["recovery_error"] = recovery_error
        return state

    def diagnostics(self) -> dict:
        primary, primary_error = self._read_valid(self.state_path)
        backup, backup_error = self._read_valid(self.backup_path)
        selected = primary or backup
        return {
            "schema_version": int((selected or {}).get("schema_version", 1)),
            "generation": int((selected or {}).get("generation", 0) or 0),
            "primary_exists": self.state_path.exists(),
            "primary_valid": primary is not None,
            "backup_exists": self.backup_path.exists(),
            "backup_valid": backup is not None,
            "recovery_source": "primary" if primary is not None else "backup" if backup is not None else "none",
            "primary_error": primary_error,
            "backup_error": backup_error,
            "integrity_ok": primary is not None or backup is not None,
        }

    def load_positions(self) -> Dict:
        return self.load_state().get("positions", {})

    def load_pending_orders(self) -> Dict:
        return self.load_state().get("pending_orders", {})

    def load_order_guards(self) -> Dict[str, float]:
        return self.load_state().get("order_guards", {})

    def load_execution_intents(self) -> Dict[str, dict]:
        return self.load_state().get("execution_intents", {})

    def load_financial_account(self) -> Dict:
        return self.load_state().get("financial_account", {})

    def load_risk_state(self) -> Dict:
        return self.load_state().get("risk_state", {})

    def clear(self) -> None:
        if self.state_path.exists():
            self.state_path.unlink()
        if self.backup_path.exists():
            self.backup_path.unlink()
        if self.reconciliation_journal_path.exists():
            self.reconciliation_journal_path.unlink()
