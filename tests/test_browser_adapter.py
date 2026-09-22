from PC_ENGINE.core.execution_fabric import ExecutionIntent, ExecutionMethod
from PC_ENGINE.execution.browser_adapter import BrowserExecutionAdapter
from PC_ENGINE.execution.browser_execution_ledger import BrowserExecutionLedger
from PC_ENGINE.execution.browser_safety import BrowserActionProposal, BrowserElement, BrowserExecutionSafety, BrowserObservation, BrowserSafetyStatus


class Driver:
    def __init__(self, outcome="FILLED"):
        self.outcome = outcome
        self.submissions = 0

    def observe(self, intent):
        return BrowserObservation.from_elements(page_fingerprint="page-1", context_fingerprint="ctx-1", observed_ts_ms=1000, elements=(BrowserElement("buy", "button", "Buy"),))

    def submit(self, intent, proposal, observation):
        self.submissions += 1
        return "order-1"

    def verify_exchange(self, intent, external_id):
        return self.outcome


def proposal_factory(intent, observation):
    return BrowserActionProposal("CLICK", "buy", 0.95, observation.page_fingerprint, observation.context_fingerprint)


def intent():
    return ExecutionIntent("owner-a", "binance", "acct-a", "BUY", "BTCUSDT", 0.01, ExecutionMethod.BROWSER, "idem-1")


def test_browser_adapter_requires_independent_exchange_verification():
    adapter = BrowserExecutionAdapter(Driver("FILLED"), BrowserExecutionSafety(), proposal_factory)
    result = adapter.execute(intent())
    assert result.success is True
    assert result.external_id == "order-1"


def test_browser_submission_without_exchange_confirmation_fails_closed():
    adapter = BrowserExecutionAdapter(Driver(None), BrowserExecutionSafety(), proposal_factory)
    result = adapter.execute(intent())
    assert result.success is False
    assert result.status == "EXCHANGE_OUTCOME_UNVERIFIED"


def test_browser_adapter_rejects_stale_observation():
    class StaleDriver(Driver):
        def observe(self, intent):
            return BrowserObservation.from_elements(page_fingerprint="page-1", context_fingerprint="ctx-1", observed_ts_ms=1000, elements=(BrowserElement("buy", "button", "Buy", True, True, False),))
    def stale_proposal(intent, observation):
        return BrowserActionProposal("CLICK", "buy", 0.95, "page-old", observation.context_fingerprint)
    adapter = BrowserExecutionAdapter(StaleDriver(), BrowserExecutionSafety(), stale_proposal)
    result = adapter.execute(intent())
    assert result.status == BrowserSafetyStatus.STALE.value
    assert result.success is False


def test_browser_adapter_persists_submission_before_and_after_exchange_verification(tmp_path):
    driver = Driver("FILLED")
    ledger = BrowserExecutionLedger(tmp_path / "browser.jsonl")
    adapter = BrowserExecutionAdapter(driver, BrowserExecutionSafety(), proposal_factory, ledger=ledger)
    result = adapter.execute(intent())
    assert result.success is True
    assert driver.submissions == 1
    assert ledger.latest("idem-1").state == "VERIFIED"
    assert len((tmp_path / "browser.jsonl").read_text().splitlines()) == 3


def test_browser_adapter_never_blindly_reclicks_existing_submission(tmp_path):
    driver = Driver("FILLED")
    ledger = BrowserExecutionLedger(tmp_path / "browser.jsonl")
    adapter = BrowserExecutionAdapter(driver, BrowserExecutionSafety(), proposal_factory, ledger=ledger)
    ledger.append(intent=intent(), state="SUBMITTED", external_id="order-1", page_fingerprint="page-1", context_fingerprint="ctx-1")
    result = adapter.execute(intent())
    assert result.success is False
    assert result.status == "RECOVER_EXISTING_BROWSER_SUBMISSION"
    assert result.external_id == "order-1"
    assert driver.submissions == 0
