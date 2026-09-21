from PC_ENGINE.core.auxiliary_execution import (
    AccountRegistry, AndroidExecutor, AuxiliaryExecutionState, BrowserExecutor, ExecutionAccount,
)


class FakeBridge:
    def __init__(self, ok=True):
        self.ok = ok
        self.human = False
    def connect(self, target): return self.ok
    def navigate(self, target): return self.ok
    def submit(self, action, payload): return self.ok
    def verify(self, action): return self.ok
    def human_required(self, reason): self.human = True


def test_registry_never_persists_credentials():
    r = AccountRegistry()
    r.register(ExecutionAccount("andre", "binance", "spot-1", android_package="pkg", allow_trade=True))
    assert r.get(owner_id="andre", venue_id="binance", account_id="spot-1") is not None
    assert r.snapshot()[0]["credentials_persisted"] is False


def test_android_owner_boundary():
    account = ExecutionAccount("andre", "binance", "spot-1", android_package="pkg", allow_trade=True)
    try:
        AndroidExecutor(owner_id="diogo", account=account, bridge=FakeBridge())
        assert False
    except PermissionError:
        pass


def test_android_human_bridge_for_security_challenge():
    account = ExecutionAccount("andre", "binance", "spot-1", android_package="pkg", allow_trade=True)
    e = AndroidExecutor(owner_id="andre", account=account, bridge=FakeBridge())
    state = e.execute(action="trade", target="trade", payload={"human_required": True, "reason": "MFA"})
    assert state == AuxiliaryExecutionState.HUMAN_REQUIRED


def test_browser_success_path():
    account = ExecutionAccount("andre", "bingx", "spot-1", browser_origin="https://bingx.com", allow_trade=True)
    e = BrowserExecutor(owner_id="andre", account=account, bridge=FakeBridge())
    assert e.execute(action="trade", target="trade", payload={}) == AuxiliaryExecutionState.DONE


def test_withdrawal_is_not_enabled_by_default():
    account = ExecutionAccount("andre", "binance", "spot-1", android_package="pkg", allow_trade=True)
    e = AndroidExecutor(owner_id="andre", account=account, bridge=FakeBridge())
    assert e.execute(action="withdraw", target="withdraw", payload={}) == AuxiliaryExecutionState.FAILED
