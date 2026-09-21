from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class AuxiliaryExecutionState(str, Enum):
    CONNECTING = "CONNECTING"
    READY = "READY"
    NAVIGATING = "NAVIGATING"
    INPUT = "INPUT"
    SUBMITTING = "SUBMITTING"
    VERIFYING = "VERIFYING"
    DONE = "DONE"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ExecutionAccount:
    owner_id: str
    venue_id: str
    account_id: str
    enabled: bool = True
    android_package: str | None = None
    browser_origin: str | None = None
    allow_trade: bool = False
    allow_deposit: bool = False
    allow_withdrawal: bool = False


class AccountRegistry:
    """Owner-private execution target metadata; never stores credentials."""

    def __init__(self) -> None:
        self._accounts: dict[tuple[str, str, str], ExecutionAccount] = {}

    def register(self, account: ExecutionAccount) -> None:
        if not account.owner_id or not account.venue_id or not account.account_id:
            raise ValueError("owner_id, venue_id and account_id are required")
        key = (account.owner_id, account.venue_id, account.account_id)
        self._accounts[key] = account

    def get(self, *, owner_id: str, venue_id: str, account_id: str) -> ExecutionAccount | None:
        return self._accounts.get((owner_id, venue_id, account_id))

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "owner_id": a.owner_id, "venue_id": a.venue_id,
                "account_id": a.account_id, "enabled": a.enabled,
                "android_package": a.android_package,
                "browser_origin": a.browser_origin,
                "allow_trade": a.allow_trade,
                "allow_deposit": a.allow_deposit,
                "allow_withdrawal": a.allow_withdrawal,
                "credentials_persisted": False,
            }
            for a in self._accounts.values()
        ]


class DeviceBridge(Protocol):
    def connect(self, package: str) -> bool: ...
    def navigate(self, target: str) -> bool: ...
    def submit(self, action: str, payload: dict[str, Any]) -> bool: ...
    def verify(self, action: str) -> bool: ...
    def human_required(self, reason: str) -> None: ...


class AndroidExecutor:
    """Stateful Android auxiliary executor.

    It is deliberately an adapter contract: ADB/Appium/device integrations can
    implement DeviceBridge. MFA, CAPTCHA and biometric prompts always escalate
    to Human Bridge instead of bypassing platform security.
    """

    def __init__(self, *, owner_id: str, account: ExecutionAccount, bridge: DeviceBridge):
        if account.owner_id != owner_id:
            raise PermissionError("OWNER_BOUNDARY")
        self.owner_id = owner_id
        self.account = account
        self.bridge = bridge
        self.state = AuxiliaryExecutionState.CONNECTING

    def execute(self, *, action: str, target: str, payload: dict[str, Any]) -> AuxiliaryExecutionState:
        if not self.account.enabled:
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        if action == "withdraw" and not self.account.allow_withdrawal:
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        if action == "trade" and not self.account.allow_trade:
            self.state = AuxiliaryExecutionState.FAILED
            return self.state

        if not self.bridge.connect(self.account.android_package or ""):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        self.state = AuxiliaryExecutionState.READY

        if not self.bridge.navigate(target):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        self.state = AuxiliaryExecutionState.NAVIGATING

        self.state = AuxiliaryExecutionState.INPUT
        if payload.get("human_required"):
            self.state = AuxiliaryExecutionState.HUMAN_REQUIRED
            self.bridge.human_required(str(payload.get("reason", "platform security challenge")))
            return self.state

        self.state = AuxiliaryExecutionState.SUBMITTING
        if not self.bridge.submit(action, payload):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state

        self.state = AuxiliaryExecutionState.VERIFYING
        if not self.bridge.verify(action):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        self.state = AuxiliaryExecutionState.DONE
        return self.state


class BrowserExecutor:
    """Browser auxiliary executor with the same owner/account boundary."""

    def __init__(self, *, owner_id: str, account: ExecutionAccount, bridge: DeviceBridge):
        if account.owner_id != owner_id:
            raise PermissionError("OWNER_BOUNDARY")
        self.owner_id = owner_id
        self.account = account
        self.bridge = bridge
        self.state = AuxiliaryExecutionState.CONNECTING

    def execute(self, *, action: str, target: str, payload: dict[str, Any]) -> AuxiliaryExecutionState:
        if not self.account.enabled or not self.account.browser_origin:
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        if action == "withdraw" and not self.account.allow_withdrawal:
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        if action == "trade" and not self.account.allow_trade:
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        if not self.bridge.connect(self.account.browser_origin):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        self.state = AuxiliaryExecutionState.READY
        if not self.bridge.navigate(target):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        self.state = AuxiliaryExecutionState.NAVIGATING
        self.state = AuxiliaryExecutionState.INPUT
        if payload.get("human_required"):
            self.state = AuxiliaryExecutionState.HUMAN_REQUIRED
            self.bridge.human_required(str(payload.get("reason", "platform security challenge")))
            return self.state
        self.state = AuxiliaryExecutionState.SUBMITTING
        if not self.bridge.submit(action, payload):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        self.state = AuxiliaryExecutionState.VERIFYING
        if not self.bridge.verify(action):
            self.state = AuxiliaryExecutionState.FAILED
            return self.state
        self.state = AuxiliaryExecutionState.DONE
        return self.state
