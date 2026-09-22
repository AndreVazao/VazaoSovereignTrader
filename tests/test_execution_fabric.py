from PC_ENGINE.core.execution_fabric import (
    ExecutionFabric,
    ExecutionMethod,
    ExecutionResult,
    ExecutionTarget,
)


class StubAdapter:
    def __init__(self, method):
        self.method = method

    def execute(self, intent):
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


def test_android_executor_is_supported_without_credentials_in_target():
    fabric = ExecutionFabric(
        owner_id="andre",
        adapters={ExecutionMethod.ANDROID: StubAdapter(ExecutionMethod.ANDROID)},
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
