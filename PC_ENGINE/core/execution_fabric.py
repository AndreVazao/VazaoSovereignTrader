from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class ExecutionMethod(str, Enum):
    API = "API"
    BROWSER = "BROWSER"
    ANDROID = "ANDROID"
    HUMAN = "HUMAN"


@dataclass(frozen=True)
class ExecutionTarget:
    owner_id: str
    venue_id: str
    account_id: str
    methods: tuple[ExecutionMethod, ...]
    enabled: bool = True
    credentials_private: bool = True
    android_package: str | None = None


@dataclass(frozen=True)
class ExecutionIntent:
    owner_id: str
    venue_id: str
    account_id: str
    action: str
    symbol: str
    quantity: float
    method: ExecutionMethod
    idempotency_key: str


@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    status: str
    method: ExecutionMethod
    external_id: str | None = None
    reason: str | None = None


class ExecutionAdapter(Protocol):
    method: ExecutionMethod

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        ...


class ExecutionFabric:
    """Owner-isolated execution routing across API, browser and Android.

    Selection is deterministic and fail-closed. This layer does not authorize
    trading; callers must already have passed RiskEngine/RealModeGuard gates.
    Human interaction is an explicit fallback, not an anti-bot bypass.
    """

    DEFAULT_PRIORITY = (
        ExecutionMethod.API,
        ExecutionMethod.BROWSER,
        ExecutionMethod.ANDROID,
        ExecutionMethod.HUMAN,
    )

    def __init__(self, *, owner_id: str, adapters: dict[ExecutionMethod, ExecutionAdapter] | None = None):
        self.owner_id = str(owner_id or "").strip().lower()
        self.adapters = dict(adapters or {})
        if not self.owner_id:
            raise ValueError("owner_id is required")

    def select_method(self, target: ExecutionTarget) -> ExecutionMethod | None:
        if target.owner_id.strip().lower() != self.owner_id:
            return None
        if not target.enabled:
            return None
        supported = set(target.methods)
        for method in self.DEFAULT_PRIORITY:
            if method in supported and method in self.adapters:
                return method
        return None

    def build_intent(
        self,
        *,
        target: ExecutionTarget,
        action: str,
        symbol: str,
        quantity: float,
        idempotency_key: str,
    ) -> ExecutionIntent | None:
        method = self.select_method(target)
        if method is None or quantity <= 0 or not idempotency_key.strip():
            return None
        return ExecutionIntent(
            owner_id=self.owner_id,
            venue_id=target.venue_id,
            account_id=target.account_id,
            action=str(action).upper().strip(),
            symbol=str(symbol).upper().strip(),
            quantity=float(quantity),
            method=method,
            idempotency_key=idempotency_key.strip(),
        )

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        if intent.owner_id.strip().lower() != self.owner_id:
            return ExecutionResult(False, "OWNER_MISMATCH", intent.method, reason="owner isolation")
        adapter = self.adapters.get(intent.method)
        if adapter is None:
            return ExecutionResult(False, "ADAPTER_UNAVAILABLE", intent.method, reason="no adapter")
        return adapter.execute(intent)

    @staticmethod
    def snapshot(targets: list[ExecutionTarget]) -> dict[str, Any]:
        return {
            "owner_private": True,
            "execution_authority": "GATED_BY_CALLER",
            "targets": [
                {
                    "owner_id": t.owner_id,
                    "venue_id": t.venue_id,
                    "account_id": t.account_id,
                    "methods": [m.value for m in t.methods],
                    "enabled": t.enabled,
                    "credentials_private": t.credentials_private,
                    "android_package": t.android_package,
                }
                for t in targets
            ],
        }
