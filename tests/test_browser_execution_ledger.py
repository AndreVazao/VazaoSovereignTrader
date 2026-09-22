from PC_ENGINE.core.execution_fabric import ExecutionIntent, ExecutionMethod
from PC_ENGINE.execution.browser_execution_ledger import BrowserExecutionLedger


def test_browser_ledger_is_append_only_and_idempotent_lookup(tmp_path):
    ledger = BrowserExecutionLedger(tmp_path / "browser.jsonl")
    intent = ExecutionIntent("owner-a", "binance", "acct-a", "BUY", "BTCUSDT", 0.01, ExecutionMethod.BROWSER, "idem-1")
    ledger.append(intent=intent, state="SUBMITTED", external_id="order-1", page_fingerprint="p1", context_fingerprint="c1")
    ledger.append(intent=intent, state="VERIFIED", external_id="order-1", page_fingerprint="p1", context_fingerprint="c1")
    latest = ledger.latest("idem-1")
    assert latest is not None
    assert latest.state == "VERIFIED"
    assert latest.external_id == "order-1"
    assert len((tmp_path / "browser.jsonl").read_text().splitlines()) == 2


def test_browser_ledger_keeps_owner_identity(tmp_path):
    ledger = BrowserExecutionLedger(tmp_path / "browser.jsonl")
    intent = ExecutionIntent("owner-a", "binance", "acct-a", "SELL", "BTCUSDT", 0.02, ExecutionMethod.BROWSER, "idem-2")
    item = ledger.append(intent=intent, state="SUBMITTED", external_id="order-2", page_fingerprint="p1", context_fingerprint="c1")
    assert item.owner_id == "owner-a"
    assert ledger.latest("idem-2").owner_id == "owner-a"
