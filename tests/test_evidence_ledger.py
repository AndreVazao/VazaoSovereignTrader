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
