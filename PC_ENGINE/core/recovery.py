from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterator

from PC_ENGINE.core.config import DATA_DIR


SCHEMA_VERSION = 2
JOURNAL_SCHEMA_VERSION = 1


class RecoveryLockError(RuntimeError):
    """Recovery transaction lock could not be acquired or released safely."""


@contextmanager
def _recovery_file_lock(path: Path) -> Iterator[object]:
    """Serialize recovery transactions across processes with an OS file lock."""
    lock_path = path.with_name(f"{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    try:
        handle = lock_path.open("a+b")
        handle.seek(0)
        if handle.read(1) == b"":
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
        handle.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

        yield handle
    except (OSError, ValueError) as exc:
        raise RecoveryLockError("recovery transaction lock unavailable") from exc
    finally:
        if handle is not None:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (OSError, ValueError):
                pass
            finally:
                handle.close()


def _canonical_payload(payload: dict) -> bytes:
    body = dict(payload)
    body.pop("integrity_sha256", None)
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(payload: dict) -> str:
    return hashlib.sha256(_canonical_payload(payload)).hexdigest()


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
        self.reconciliation_lock_path = state_path.with_suffix(state_path.suffix + ".reconciliation.lock")
        self._reconciliation_lock_handle = None

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
            pass

    def _write_json_atomic(self, path: Path, payload: dict) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with tmp_path.open("r+", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
        self._fsync_directory(path.parent)

    def _acquire_reconciliation_lock(self) -> None:
        if self._reconciliation_lock_handle is not None:
            raise RecoveryLockError("reconciliation transaction lock already held by this manager")
        manager = _recovery_file_lock(self.reconciliation_lock_path)
        handle = manager.__enter__()
        self._reconciliation_lock_handle = (manager, handle)

    def _release_reconciliation_lock(self) -> None:
        held = self._reconciliation_lock_handle
        self._reconciliation_lock_handle = None
        if held is None:
            return
        manager, _handle = held
        manager.__exit__(None, None, None)

    def prepare_reconciliation(self, target_state: dict, ledger_records: list[dict] | None = None) -> str:
        """Durably prepare one recovery transaction and reserve the journal writer."""
        import uuid

        self._acquire_reconciliation_lock()
        try:
            current, _ = self._read_valid(self.state_path)
            generation = int((current or {}).get("generation", 0) or 0) + 1
            payload = dict(target_state)
            payload["schema_version"] = SCHEMA_VERSION
            payload["generation"] = generation
            payload["ts"] = int(time.time())
            payload["integrity_sha256"] = _digest(payload)
            transaction = {
                "schema_version": JOURNAL_SCHEMA_VERSION,
                "transaction_id": uuid.uuid4().hex,
                "target_state": payload,
                "ledger_records": list(ledger_records or []),
            }
            transaction["integrity_sha256"] = _digest(transaction)
            self._write_json_atomic(self.reconciliation_journal_path, transaction)
            return str(transaction["transaction_id"])
        except Exception:
            self._release_reconciliation_lock()
            raise

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
        acquired_here = False
        if self._reconciliation_lock_handle is None:
            self._acquire_reconciliation_lock()
            acquired_here = True
        try:
            journal = self.load_reconciliation_journal()
            if journal is None or str(journal.get("transaction_id")) != str(transaction_id):
                raise RuntimeError("reconciliation transaction missing or mismatched")
            target = dict(journal["target_state"])
            self._write_json_atomic(self.state_path, target)
            self._write_json_atomic(self.backup_path, target)
        except Exception:
            if acquired_here:
                self._release_reconciliation_lock()
            raise

    def clear_reconciliation(self) -> None:
        acquired_here = False
        if self.reconciliation_journal_path.exists() and self._reconciliation_lock_handle is None:
            self._acquire_reconciliation_lock()
            acquired_here = True
        try:
            if self.reconciliation_journal_path.exists():
                self.reconciliation_journal_path.unlink()
                self._fsync_directory(self.reconciliation_journal_path.parent)
        finally:
            if acquired_here or self._reconciliation_lock_handle is not None:
                self._release_reconciliation_lock()

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
        try:
            if self.state_path.exists():
                self.state_path.unlink()
            if self.backup_path.exists():
                self.backup_path.unlink()
            if self.reconciliation_journal_path.exists():
                self.reconciliation_journal_path.unlink()
        finally:
            self._release_reconciliation_lock()
