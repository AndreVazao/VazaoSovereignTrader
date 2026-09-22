from PC_ENGINE.execution.browser_safety import (
    BrowserActionProposal,
    BrowserElement,
    BrowserExecutionSafety,
    BrowserFreshnessGuard,
    BrowserObservation,
    BrowserSafetyStatus,
    fingerprint_context,
)


def observation():
    return BrowserObservation.from_elements(
        page_fingerprint="page-a",
        context_fingerprint="ctx-a",
        observed_ts_ms=1000,
        elements=(BrowserElement("submit-1", "button", "Buy", True, True, False),),
    )


def test_indexed_target_is_authorized_when_observation_is_fresh():
    o = observation()
    p = BrowserActionProposal("CLICK", "submit-1", 0.9, "page-a", "ctx-a")
    assert BrowserFreshnessGuard().validate(o, p) == BrowserSafetyStatus.READY


def test_stale_page_fails_closed():
    o = observation()
    p = BrowserActionProposal("CLICK", "submit-1", 0.9, "page-b", "ctx-a")
    assert BrowserFreshnessGuard().validate(o, p) == BrowserSafetyStatus.STALE


def test_missing_target_fails_closed():
    o = observation()
    p = BrowserActionProposal("CLICK", "submit-2", 0.9, "page-a", "ctx-a")
    assert BrowserFreshnessGuard().validate(o, p) == BrowserSafetyStatus.TARGET_INVALID


def test_covered_target_fails_closed():
    o = BrowserObservation.from_elements(page_fingerprint="page-a", context_fingerprint="ctx-a", observed_ts_ms=1000, elements=(BrowserElement("submit-1", "button", "Buy", True, True, True),))
    p = BrowserActionProposal("CLICK", "submit-1", 0.9, "page-a", "ctx-a")
    assert BrowserFreshnessGuard().validate(o, p) == BrowserSafetyStatus.COVERED


def test_forbidden_execution_payloads_are_not_accepted():
    o = observation()
    assert BrowserExecutionSafety().authorize(o, BrowserActionProposal("JAVASCRIPT", "submit-1", 1.0, "page-a", "ctx-a")) == BrowserSafetyStatus.TARGET_INVALID
    assert BrowserExecutionSafety().authorize(o, BrowserActionProposal("CAPTCHA", "submit-1", 1.0, "page-a", "ctx-a")) == BrowserSafetyStatus.HUMAN_REQUIRED


def test_exchange_verification_is_independent_of_browser_submission():
    v = BrowserExecutionSafety.verify_exchange_outcome(exchange_status=None)
    assert v.status == BrowserSafetyStatus.OUTCOME_UNVERIFIED
    v = BrowserExecutionSafety.verify_exchange_outcome(exchange_status="FILLED", external_id="ex-1")
    assert v.status == BrowserSafetyStatus.READY


def test_context_fingerprint_is_deterministic():
    assert fingerprint_context(("venue", "order-form", "BTCUSDT")) == fingerprint_context(("venue", "order-form", "BTCUSDT"))
