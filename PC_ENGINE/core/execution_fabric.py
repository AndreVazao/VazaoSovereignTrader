from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


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
    """Owner-isolated executor selection.

    RiskEngine/RealModeGuard remain the authorization boundary. This layer
    chooses an already-authorized transport and never bypasses MFA/CAPTCHA or
    other platform security controls.
    """

    PRIORITY = (
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
        if target.owner_id.strip().lower() != self.owner_id or not target.enabled:
            return None
        supported = set(target.methods)
        return next((m for m in self.PRIORITY if m in supported and m in self.adapters), None)

    def build_intent(self, *, target: ExecutionTarget, action: str, symbol: str, quantity: float, idempotency_key: str) -> ExecutionIntent | None:
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
