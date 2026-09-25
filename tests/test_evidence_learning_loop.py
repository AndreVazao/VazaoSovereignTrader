from PC_ENGINE.learning.evidence_learning_loop import PaperEvidenceLearningLoop
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger, EvidenceLedgerRecord, EvidencePlaneSummary


def _record(ts: int, eligible: bool, *, candidate: str = "cand", version: str = "1", symbol: str = "BTC/USDT", regime: str = "BULL"):
    plane = EvidencePlaneSummary("durable", "PASS" if eligible else "FAIL", 30, 2, 2 if eligible else 1, 5.0 if eligible else -1.0, 1.0 if eligible else -2.0, 1.0 if eligible else -2.0, 1.0 if eligible else 0.0, 2)
    return EvidenceLedger.with_digest(EvidenceLedgerRecord(
        created_at_ms=ts,
        candidate_id=candidate,
        version=version,
        strategy="momentum",
        symbol=symbol,
        regime=regime,
        horizon_ms=5000,
        eligible=eligible,
        reason="ok" if eligible else "insufficient evidence",
        reason_codes=() if eligible else ("insufficient_evidence",),
        data_start_ms=ts - 10000,
        data_end_ms=ts,
        state_count=30,
        outcome_count=30,
        durable_outcome=plane,
        chronological_oos=plane,
        source_digest="0" * 64,
    ))


def test_learning_loop_detects_recent_degradation():
    records = [_record(i, True) for i in range(1, 5)] + [_record(5, False), _record(6, False)]
    snapshot = PaperEvidenceLearningLoop(recent_records=2, degradation_threshold=0.20).evaluate(records)
    assert snapshot.degradation_detected
    assert snapshot.recent_eligibility_ratio == 0.0
    assert snapshot.historical_eligibility_ratio == 1.0
    assert snapshot.actions[0].action == "INVESTIGATE"


def test_learning_loop_marks_latest_candidate_observation_for_investigation():
    records = [
        _record(1, True),
        _record(2, False),
        _record(3, True),
        _record(4, False),
    ]
    snapshot = PaperEvidenceLearningLoop(recent_records=2, degradation_threshold=0.20).evaluate(records)
    assert snapshot.degradation_detected
    assert snapshot.actions[0].action == "OBSERVE"


def test_learning_loop_never_mutates_or_authorizes_evidence():
    records = [_record(1, True)]
    before = records[0].to_dict()
    snapshot = PaperEvidenceLearningLoop().evaluate(records)
    assert records[0].to_dict() == before
    assert snapshot.actions[0].action == "OBSERVE"
