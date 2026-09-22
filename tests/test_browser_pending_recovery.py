from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine
from PC_ENGINE.core.execution_fabric import ExecutionIntent, ExecutionMethod
from PC_ENGINE.execution.browser_execution_ledger import BrowserExecutionLedger


def test_engine_recovers_submitted_browser_order_into_pending_orders(tmp_path):
    ledger = BrowserExecutionLedger(tmp_path / "browser.jsonl")
    intent = ExecutionIntent("owner-a", "fake", "acct-a", "BUY", "BTC/USDT", 0.25, ExecutionMethod.BROWSER, "browser-idem-1")
    ledger.append(intent=intent, state="SUBMITTED", external_id="browser-order-1", page_fingerprint="p1", context_fingerprint="c1")

    engine = object.__new__(SovereignEngine)
    engine.browser_execution_ledger = ledger
    engine.state = RuntimeState(status="OFF", mode="PAPER")
    engine._enter_safe_state = lambda reason: setattr(engine.state, "status", "SAFE_MODE")
    engine.log = lambda *args, **kwargs: None
    engine._recover_browser_submissions()

    recovered = engine.state.pending_orders["browser-order-1"]
    assert recovered["symbol"] == "BTC/USDT"
    assert recovered["side"] == "buy"
    assert recovered["requested_qty"] == 0.25
    assert recovered["browser_execution"] is True
    assert engine.state.status == "SAFE_MODE"


def test_engine_does_not_recover_verified_browser_order(tmp_path):
    ledger = BrowserExecutionLedger(tmp_path / "browser.jsonl")
    intent = ExecutionIntent("owner-a", "fake", "acct-a", "SELL", "BTC/USDT", 0.10, ExecutionMethod.BROWSER, "browser-idem-2")
    ledger.append(intent=intent, state="SUBMITTED", external_id="browser-order-2", page_fingerprint="p1", context_fingerprint="c1")
    ledger.append(intent=intent, state="VERIFIED", external_id="browser-order-2", page_fingerprint="p1", context_fingerprint="c1")

    engine = object.__new__(SovereignEngine)
    engine.browser_execution_ledger = ledger
    engine.state = RuntimeState(status="OFF", mode="PAPER")
    engine._enter_safe_state = lambda reason: setattr(engine.state, "status", "SAFE_MODE")
    engine.log = lambda *args, **kwargs: None
    engine._recover_browser_submissions()
    assert engine.state.pending_orders == {}
