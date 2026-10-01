from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from PC_ENGINE.core.identity import AuthenticatedPrincipal


DEVICE_SCOPES = frozenset({"read_private_state", "trade_paper"})
CHALLENGE_TTL_SECONDS = 300
MAX_DEVICES = 50
MAX_CHALLENGES = 100


class MobilePairingStore:
    """Local, revocable device-token registry. Raw device tokens are never persisted."""

    def __init__(self, data_dir: str | Path, owner_id: str = "andre"):
        self.root = Path(data_dir)
        self.path = self.root / "mobile_pairing.json"
        self.owner_id = str(owner_id).strip().lower()
        self._lock = threading.RLock()

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _read(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"version": 1, "challenges": {}, "devices": {}}
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("mobile_pairing_store_unreadable") from exc
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise RuntimeError("mobile_pairing_store_invalid")
        if not isinstance(payload.get("challenges"), dict) or not isinstance(payload.get("devices"), dict):
            raise RuntimeError("mobile_pairing_store_invalid")
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp, 0o600)
            except OSError:
                pass
            os.replace(temp, self.path)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _expire(payload: dict[str, Any], now: int) -> None:
        for item in payload["challenges"].values():
            if item.get("status") in {"PENDING", "APPROVED"} and int(item.get("expires_at", 0)) <= now:
                item["status"] = "EXPIRED"

    def create_challenge(self, device_name: str) -> dict[str, Any]:
        name = " ".join(str(device_name or "").split())[:60]
        if not name:
            raise ValueError("device_name_required")
        now = int(time.time())
        challenge_id = secrets.token_urlsafe(24)
        code = f"{secrets.randbelow(1_000_000):06d}"
        with self._lock:
            payload = self._read()
            self._expire(payload, now)
            payload["challenges"] = {
                key: value for key, value in payload["challenges"].items()
                if int(value.get("created_at", 0)) >= now - 86400
            }
            if len(payload["challenges"]) >= MAX_CHALLENGES:
                raise RuntimeError("too_many_pairing_challenges")
            payload["challenges"][challenge_id] = {
                "challenge_id": challenge_id,
                "device_name": name,
                "owner_id": self.owner_id,
                "confirmation_hash": self._hash(code),
                "created_at": now,
                "expires_at": now + CHALLENGE_TTL_SECONDS,
                "status": "PENDING",
            }
            self._write(payload)
        return {
            "challenge_id": challenge_id,
            "confirmation_code": code,
            "expires_at": now + CHALLENGE_TTL_SECONDS,
            "status": "PENDING",
            "paper_only": True,
            "execution_authorized": False,
        }

    def list_pending(self) -> list[dict[str, Any]]:
        now = int(time.time())
        with self._lock:
            payload = self._read()
            self._expire(payload, now)
            self._write(payload)
            return [
                {key: item[key] for key in ("challenge_id", "device_name", "created_at", "expires_at", "status")}
                for item in payload["challenges"].values()
                if item.get("status") == "PENDING"
            ]

    def approve(self, challenge_id: str, confirmation_code: str) -> dict[str, Any]:
        now = int(time.time())
        with self._lock:
            payload = self._read()
            self._expire(payload, now)
            item = payload["challenges"].get(str(challenge_id))
            if not item or item.get("status") != "PENDING":
                raise ValueError("challenge_not_pending_or_expired")
            supplied = self._hash(str(confirmation_code or "").strip())
            if not hmac.compare_digest(supplied, str(item.get("confirmation_hash", ""))):
                raise PermissionError("confirmation_code_invalid")
            item["status"] = "APPROVED"
            item["approved_at"] = now
            self._write(payload)
            return {
                "challenge_id": item["challenge_id"],
                "device_name": item["device_name"],
                "status": item["status"],
                "approved_at": now,
            }

    def challenge_status(self, challenge_id: str) -> dict[str, Any]:
        now = int(time.time())
        with self._lock:
            payload = self._read()
            self._expire(payload, now)
            self._write(payload)
            item = payload["challenges"].get(str(challenge_id))
            if not item:
                raise ValueError("challenge_not_found")
            return {
                "challenge_id": item["challenge_id"],
                "device_name": item["device_name"],
                "status": item["status"],
                "expires_at": item["expires_at"],
            }

    def complete(self, challenge_id: str, confirmation_code: str) -> dict[str, Any]:
        now = int(time.time())
        with self._lock:
            payload = self._read()
            self._expire(payload, now)
            item = payload["challenges"].get(str(challenge_id))
            if not item or item.get("status") != "APPROVED":
                raise ValueError("challenge_not_approved_or_expired")
            supplied = self._hash(str(confirmation_code or "").strip())
            if not hmac.compare_digest(supplied, str(item.get("confirmation_hash", ""))):
                raise PermissionError("confirmation_code_invalid")
            if len(payload["devices"]) >= MAX_DEVICES:
                active_count = sum(1 for device in payload["devices"].values() if device.get("status") == "ACTIVE")
                if active_count >= MAX_DEVICES:
                    raise RuntimeError("device_limit_reached")
            device_id = secrets.token_urlsafe(18)
            token = secrets.token_urlsafe(48)
            payload["devices"][device_id] = {
                "device_id": device_id,
                "device_name": item["device_name"],
                "owner_id": self.owner_id,
                "token_hash": self._hash(token),
                "scopes": sorted(DEVICE_SCOPES),
                "status": "ACTIVE",
                "created_at": now,
                "last_seen_at": now,
            }
            item["status"] = "COMPLETED"
            item["completed_at"] = now
            item["device_id"] = device_id
            self._write(payload)
            return {
                "device_id": device_id,
                "device_name": item["device_name"],
                "device_token": token,
                "scopes": sorted(DEVICE_SCOPES),
                "status": "ACTIVE",
                "paper_only": True,
                "orders_submitted": False,
                "execution_authorized": False,
            }

    def authenticate(self, token: str) -> AuthenticatedPrincipal | None:
        if not token:
            return None
        token_hash = self._hash(token)
        now = int(time.time())
        with self._lock:
            payload = self._read()
            for device_id, item in payload["devices"].items():
                if item.get("status") != "ACTIVE":
                    continue
                if hmac.compare_digest(token_hash, str(item.get("token_hash", ""))):
                    last_seen = int(item.get("last_seen_at", 0))
                    if now - last_seen >= 60:
                        item["last_seen_at"] = now
                        self._write(payload)
                    return AuthenticatedPrincipal(
                        user_id=str(item.get("owner_id", self.owner_id)),
                        owner_id=str(item.get("owner_id", self.owner_id)),
                        device_id=device_id,
                        scopes=DEVICE_SCOPES,
                        auth_method="mobile_device_token",
                    )
        return None

    def list_devices(self) -> list[dict[str, Any]]:
        with self._lock:
            payload = self._read()
            return [
                {key: item.get(key) for key in ("device_id", "device_name", "status", "created_at", "last_seen_at", "scopes")}
                for item in payload["devices"].values()
            ]

    def revoke(self, device_id: str) -> dict[str, Any]:
        with self._lock:
            payload = self._read()
            item = payload["devices"].get(str(device_id))
            if not item:
                raise ValueError("device_not_found")
            item["status"] = "REVOKED"
            item["revoked_at"] = int(time.time())
            self._write(payload)
            return {"device_id": device_id, "status": "REVOKED", "revoked": True}
