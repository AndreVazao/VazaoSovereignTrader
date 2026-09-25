from __future__ import annotations

import json

import pytest

from PC_ENGINE.radar.evidence_ledger import (
    EvidenceLedger,
    EvidenceLedgerRecord,
    EvidencePlaneSummary,
)


def make_record() -> EvidenceLedgerRecord:
    return EvidenceLedgerRecord(
        created_at_ms=1_800_000_000_000,
        candidate_id="candidate-a",
        version="v3",
        strategy="momentum",
        symbol="BTCUSDT",
        regime="trend",
        horizon_ms=60_000,
        eligible=False,
        reason="durable outcome gate failed; chronological OOS gate failed",
        reason_codes=(
            "durable outcome gate failed",
            "chronological OOS gate failed",
        ),
        data_start_ms=1_700_000_000_000,
        data_end_ms=1_800_000_000_000,
        state_count=500,
        outcome_count=240,
        durable_outcome=EvidencePlaneSummary(
            name="durable_outcome",
            status="FAIL",
            samples=240,
            scenarios=4,
            validated_scenarios=2,
            mean_net_bps=1.2,
            lower_ci_bps=-0.4,
            bootstrap_lower_ci_bps=-0.2,
            positive_fold_ratio=0.5,
            folds=4,
        ),
        chronological_oos=EvidencePlaneSummary(
            name="chronological_oos",
            status="FAIL",
            samples=120,
            scenarios=4,
            validated_scenarios=1,
            mean_net_bps=0.8,
            lower_ci_bps=-0.7,
            bootstrap_lower_ci_bps=-0.5,
            positive_fold_ratio=0.5,
            folds=3,
        ),
        source_digest="0" * 64,
    )


def test_append_round_trip_and_digest(tmp_path):
    path = tmp_path / "evidence.jsonl"
    saved = EvidenceLedger.append(path, make_record())

    assert saved.source_digest == EvidenceLedger.digest(saved)
    loaded = EvidenceLedger.load(path)

    assert loaded == [saved]
    assert loaded[0].candidate_id == "candidate-a"
    assert loaded[0].version == "v3"


def test_tampering_is_rejected(tmp_path):
    path = tmp_path / "evidence.jsonl"
    saved = EvidenceLedger.append(path, make_record())

    payload = saved.to_dict()
    payload["eligible"] = True
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source digest mismatch"):
        EvidenceLedger.load(path)


def test_reason_codes_are_stable_and_empty_reason_is_empty():
    reason = "durable outcome gate failed; chronological OOS gate failed"
    assert EvidenceLedger.reason_codes(reason) == (
        "durable outcome gate failed",
        "chronological OOS gate failed",
    )
    assert EvidenceLedger.reason_codes("") == ()


def test_plane_counts_cannot_be_inconsistent(tmp_path):
    record = make_record()
    invalid = EvidenceLedgerRecord(
        **{
            **record.to_dict(),
            "source_digest": "0" * 64,
            "durable_outcome": EvidencePlaneSummary(
                **{
                    **record.durable_outcome.__dict__,
                    "validated_scenarios": 5,
                }
            ),
        }
    )

    with pytest.raises(ValueError, match="validated scenarios"):
        EvidenceLedger.append(tmp_path / "evidence.jsonl", invalid)


def test_query_filters_only_verified_records(tmp_path):
    path = tmp_path / "evidence.jsonl"
    first = EvidenceLedger.append(path, make_record())
    second = EvidenceLedger.append(
        path,
        EvidenceLedgerRecord(
            **{
                **first.to_dict(),
                "created_at_ms": first.created_at_ms + 1,
                "candidate_id": "candidate-b",
                "version": "v1",
                "symbol": "ETHUSDT",
                "eligible": True,
                "reason": "",
                "reason_codes": (),
            }
        ),
    )

    selected = EvidenceLedger.query(
        path,
        candidate_id="candidate-b",
        symbol="ETHUSDT",
        eligible=True,
    )
    assert selected == [second]

    path.write_text(
        path.read_text(encoding="utf-8").replace('"eligible":true', '"eligible":false', 1),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source digest mismatch"):
        EvidenceLedger.query(path)


def test_summary_is_deterministic_and_counts_reason_codes(tmp_path):
    path = tmp_path / "evidence.jsonl"
    first = EvidenceLedger.append(path, make_record())
    EvidenceLedger.append(
        path,
        EvidenceLedgerRecord(
            **{
                **first.to_dict(),
                "created_at_ms": first.created_at_ms + 10,
                "candidate_id": "candidate-b",
                "version": "v1",
                "eligible": True,
                "reason": "",
                "reason_codes": (),
            }
        ),
    )

    summary = EvidenceLedger.summarize(EvidenceLedger.load(path))
    assert summary.records == 2
    assert summary.eligible_records == 1
    assert summary.rejected_records == 1
    assert summary.candidate_versions == ("candidate-a@v3", "candidate-b@v1")
    assert summary.reason_counts == (
        ("chronological OOS gate failed", 1),
        ("durable outcome gate failed", 1),
    )
    assert summary.latest_created_at_ms == first.created_at_ms + 10

def test_audit_report_is_deterministic_and_tracks_temporal_coverage(tmp_path):
    path = tmp_path / "evidence.jsonl"
    first = EvidenceLedger.append(path, make_record())
    EvidenceLedger.append(
        path,
        EvidenceLedgerRecord(
            **{
                **first.to_dict(),
                "created_at_ms": first.created_at_ms + 10,
                "candidate_id": "candidate-b",
                "version": "v1",
                "symbol": "ETHUSDT",
                "regime": "range",
                "strategy": "breakout",
                "eligible": True,
                "reason": "",
                "reason_codes": (),
                "data_start_ms": first.data_start_ms + 10,
                "data_end_ms": first.data_end_ms + 10,
            }
        ),
    )

    records = EvidenceLedger.query(path)
    report = EvidenceLedger.audit_report(records)

    assert report.records == 2
    assert report.eligible_records == 1
    assert report.rejected_records == 1
    assert report.eligibility_ratio == 0.5
    assert report.candidate_versions == ("candidate-a@v3", "candidate-b@v1")
    assert report.symbols == ("BTCUSDT", "ETHUSDT")
    assert report.regimes == ("range", "trend")
    assert report.strategies == ("breakout", "momentum")
    assert report.eligible_by_candidate_version == (("candidate-a@v3", 0), ("candidate-b@v1", 1))
    assert report.records_by_symbol == (("BTCUSDT", 1), ("ETHUSDT", 1))
    assert report.records_by_regime == (("range", 1), ("trend", 1))
    assert report.first_created_at_ms == first.created_at_ms
    assert report.latest_created_at_ms == first.created_at_ms + 10
    assert report.data_start_ms == first.data_start_ms
    assert report.data_end_ms == first.data_end_ms + 10


def test_audit_report_is_empty_for_empty_verified_ledger():
    report = EvidenceLedger.audit_report([])

    assert report.records == 0
    assert report.eligible_records == 0
    assert report.eligibility_ratio == 0.0
    assert report.candidate_versions == ()
    assert report.symbols == ()
    assert report.regimes == ()
    assert report.strategies == ()
    assert report.latest_created_at_ms is None
