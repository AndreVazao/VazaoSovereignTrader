from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


DEFAULT_OWNER_SCOPES = frozenset({
    "read_private_state",
    "trade_paper",
    "trade_real",
    "manage_exchange_accounts",
    "manage_owner_settings",
    "read_shared_intelligence",
    "publish_shared_intelligence",
})


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    owner_id: str
    device_id: str
    scopes: frozenset[str]
    auth_method: str

    def has(self, scope: str) -> bool:
        return scope in self.scopes

    def snapshot(self) -> dict:
        return {
            "user_id": self.user_id,
            "owner_id": self.owner_id,
            "device_id": self.device_id,
            "scopes": sorted(self.scopes),
            "auth_method": self.auth_method,
        }


class IdentityAuthenticator:
    """Local identity boundary with optional Tailscale device binding.

    Tokens stay in local environment variables. A Tailscale identity is an
    optional binding supplied by a trusted local/Tailscale ingress; it is not
    itself a financial authorization.
    """

    def __init__(self, config: dict, env_getter):
        self.config = config if isinstance(config, dict) else {}
        self.env_getter = env_getter
        owner_cfg = self.config.get("owner", {})
        self.default_owner = str(owner_cfg.get("id", "andre")).strip().lower()
        self.identity_cfg = self.config.get("identity", {})
        self.owners = self.identity_cfg.get("owners", {}) if isinstance(self.identity_cfg, dict) else {}

    @staticmethod
    def _scopes(raw: Iterable[str] | None) -> frozenset[str]:
        values = {str(item).strip() for item in (raw or []) if str(item).strip()}
        return frozenset(values or DEFAULT_OWNER_SCOPES)

    def authenticate(self, token: str, tailscale_identity: str = "", device_id: str = "") -> AuthenticatedPrincipal:
        token = str(token or "")
        ts_identity = str(tailscale_identity or "").strip()
        configured_owner = self.default_owner
        selected = None

        for owner_id, raw in self.owners.items():
            cfg = raw if isinstance(raw, dict) else {}
            token_env = str(cfg.get("token_env", "")).strip()
            expected = self.env_getter(token_env, "") if token_env else ""
            if expected and token and token == expected:
                configured_owner = str(owner_id).strip().lower()
                selected = cfg
                break

        if selected is None:
            fallback_env = str(
                self.config.get("server", {}).get("local_control_token_env", "VST_LOCAL_TOKEN")
            )
            expected = self.env_getter(fallback_env, "")
            if not expected or not token or token != expected:
                raise PermissionError("unauthorized")
            selected = self.owners.get(configured_owner, {})

        selected = selected if isinstance(selected, dict) else {}
        required_ts = str(selected.get("tailscale_identity", "")).strip()
        require_ts = bool(self.identity_cfg.get("require_device_identity", False))
        if required_ts and ts_identity != required_ts:
            raise PermissionError("device_identity_mismatch")
        if require_ts and not ts_identity:
            raise PermissionError("device_identity_required")

        return AuthenticatedPrincipal(
            user_id=str(selected.get("user_id", configured_owner)),
            owner_id=configured_owner,
            device_id=str(device_id or selected.get("device_id", "local")),
            scopes=self._scopes(selected.get("scopes")),
            auth_method="local_token",
        )
