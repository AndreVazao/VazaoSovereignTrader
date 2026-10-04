from PC_ENGINE.core.execution_fabric import (
    ExecutionFabric,
    ExecutionMethod,
    ExecutionResult,
    ExecutionTarget,
)


class StubAdapter:
    def __init__(self, method):
        self.method = method
        self.calls = 0

    def execute(self, intent):
        self.calls += 1
        return ExecutionResult(True, "SUBMITTED", self.method, external_id="demo")


def test_prefers_api_then_browser_then_android_then_human():
    fabric = ExecutionFabric(
        owner_id="andre",
        adapters={
            ExecutionMethod.BROWSER: StubAdapter(ExecutionMethod.BROWSER),
            ExecutionMethod.ANDROID: StubAdapter(ExecutionMethod.ANDROID),
        },
    )
    target = ExecutionTarget(
        owner_id="andre",
        venue_id="xtb",
        account_id="andre-xtb",
        methods=(ExecutionMethod.API, ExecutionMethod.BROWSER, ExecutionMethod.ANDROID),
    )
    intent = fabric.build_intent(
        target=target, action="BUY", symbol="BTC/USDT", quantity=1, idempotency_key="k1", stop_pct=0.02, take_profit_pct=0.04
    )
    assert intent is not None
    assert intent.method is ExecutionMethod.BROWSER
    assert intent.stop_pct == 0.02
    assert intent.take_profit_pct == 0.04


def test_owner_mismatch_fails_closed():
    fabric = ExecutionFabric(owner_id="andre", adapters={ExecutionMethod.ANDROID: StubAdapter(ExecutionMethod.ANDROID)})
    target = ExecutionTarget(
        owner_id="genro",
        venue_id="xtb",
        account_id="genro-xtb",
        methods=(ExecutionMethod.ANDROID,),
    )
    assert fabric.build_intent(
        target=target, action="BUY", symbol="BTC/USDT", quantity=1, idempotency_key="k1"
    ) is None


def test_android_executor_requires_explicit_per_intent_authorization():
    adapter = StubAdapter(ExecutionMethod.ANDROID)
    fabric = ExecutionFabric(
        owner_id="andre",
        adapters={ExecutionMethod.ANDROID: adapter},
        execution_authorizer=lambda intent: intent.action == "SELL" and intent.quantity > 0,
    )
    target = ExecutionTarget(
        owner_id="andre",
        venue_id="youhodler",
        account_id="andre-youhodler",
        methods=(ExecutionMethod.ANDROID,),
        android_package="com.example.finance",
    )
    intent = fabric.build_intent(
        target=target, action="SELL", symbol="ETH/USDT", quantity=0.1, idempotency_key="k2"
    )
    assert intent is not None
    assert intent.method is ExecutionMethod.ANDROID
    result = fabric.execute(intent)
    assert result.success
    assert result.status == "SUBMITTED"
    assert adapter.calls == 1


def test_direct_execution_without_authorizer_fails_closed():
    adapter = StubAdapter(ExecutionMethod.ANDROID)
    fabric = ExecutionFabric(
        owner_id="andre",
        adapters={ExecutionMethod.ANDROID: adapter},
    )
    target = ExecutionTarget(
        owner_id="andre",
        venue_id="youhodler",
        account_id="andre-youhodler",
        methods=(ExecutionMethod.ANDROID,),
    )
    intent = fabric.build_intent(
        target=target, action="SELL", symbol="ETH/USDT", quantity=0.1, idempotency_key="k3"
    )
    assert intent is not None
    result = fabric.execute(intent)
    assert not result.success
    assert result.status == "AUTHORIZATION_REQUIRED"
    assert adapter.calls == 0


def test_execution_authorizer_exception_fails_closed():
    adapter = StubAdapter(ExecutionMethod.API)

    def broken_authorizer(intent):
        raise RuntimeError("simulated gate failure")

    fabric = ExecutionFabric(
        owner_id="andre",
        adapters={ExecutionMethod.API: adapter},
        execution_authorizer=broken_authorizer,
    )
    target = ExecutionTarget(
        owner_id="andre",
        venue_id="binance",
        account_id="andre-binance",
        methods=(ExecutionMethod.API,),
    )
    intent = fabric.build_intent(
        target=target, action="BUY", symbol="BTC/USDT", quantity=0.01, idempotency_key="k4"
    )
    assert intent is not None
    result = fabric.execute(intent)
    assert not result.success
    assert result.status == "AUTHORIZATION_ERROR"
    assert adapter.calls == 0
