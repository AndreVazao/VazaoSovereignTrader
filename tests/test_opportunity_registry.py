from __future__ import annotations

import json
import unittest
from pathlib import Path

from PC_ENGINE.opportunity.registry import (
    OpportunityCategory,
    OpportunityRecord,
    OpportunityRegistry,
    OpportunityStatus,
)


def make_record(**overrides) -> OpportunityRecord:
    values = {
        "opportunity_id": "binance-grid-spot",
        "venue_id": "binance",
        "account_scope": "owner-authorized-account",
        "category": OpportunityCategory.NATIVE_AUTOMATION,
        "source_url": "https://www.binance.com/en/support/faq",
        "discovered_at_ms": 1_000,
        "source_captured_at_ms": 1_000,
    }
    values.update(overrides)
    return OpportunityRecord(**values)


class OpportunityRegistryTests(unittest.TestCase):
    def test_valid_record_round_trips_without_authorizing_execution(self) -> None:
        record = make_record(required_permissions=("read",), risk_notes=("market risk",))
        record.validate(now_ms=2_000)
        restored = OpportunityRecord.from_dict(record.to_dict())
        self.assertEqual(restored, record)
        self.assertTrue(restored.paper_only)
        self.assertFalse(restored.execution_authorized)

    def test_requires_https_source_without_embedded_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            make_record(source_url="http://example.com/offer").validate(now_ms=2_000)
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            make_record(source_url="https://user:secret@example.com/offer").validate(now_ms=2_000)

    def test_requires_discovery_and_capture_timestamps(self) -> None:
        with self.assertRaisesRegex(ValueError, "timestamps"):
            make_record(source_captured_at_ms=0).validate(now_ms=2_000)

    def test_future_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "future"):
            make_record(discovered_at_ms=400_000).validate(now_ms=1_000)

    def test_confirmed_eligibility_requires_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "eligibility"):
            make_record(status=OpportunityStatus.ELIGIBLE_CONFIRMED).validate(now_ms=2_000)

    def test_positive_value_state_requires_positive_estimate(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive estimate"):
            make_record(status=OpportunityStatus.NET_VALUE_POSITIVE_ESTIMATE).validate(now_ms=2_000)
        record = make_record(
            status=OpportunityStatus.NET_VALUE_POSITIVE_ESTIMATE,
            eligibility_evidence="official account eligibility confirmed",
            net_value_estimate=0.01,
        )
        record.validate(now_ms=2_000)

    def test_discovery_cannot_authorize_execution_or_leave_paper(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot authorize"):
            make_record(execution_authorized=True).validate(now_ms=2_000)
        with self.assertRaisesRegex(ValueError, "PAPER-only"):
            make_record(paper_only=False).validate(now_ms=2_000)

    def test_invalid_state_transition_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid opportunity status transition"):
            make_record().transition(OpportunityStatus.CLAIMED_OR_ENABLED_CONFIRMED, now_ms=2_000)

    def test_expired_opportunity_cannot_be_promoted(self) -> None:
        record = make_record(expires_at_ms=1_500)
        with self.assertRaisesRegex(ValueError, "expired opportunities"):
            record.transition(
                OpportunityStatus.ELIGIBILITY_UNKNOWN,
                now_ms=2_000,
            )
        expired = record.transition(OpportunityStatus.EXPIRED, now_ms=2_000)
        self.assertEqual(expired.status, OpportunityStatus.EXPIRED)

    def test_registry_persists_transitions_and_keeps_latest_state(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            registry = OpportunityRegistry(Path(tmp) / "opportunities.jsonl")
            record = make_record()
            registry.upsert(record, now_ms=2_000)
            updated = registry.transition(
                record.opportunity_id,
                OpportunityStatus.ELIGIBILITY_UNKNOWN,
                now_ms=3_000,
            )
            self.assertEqual(updated.status, OpportunityStatus.ELIGIBILITY_UNKNOWN)
            self.assertEqual(len(registry.list_records()), 1)
            self.assertEqual(registry.list_records()[0].status, OpportunityStatus.ELIGIBILITY_UNKNOWN)

    def test_new_registry_records_must_start_as_discovered(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            registry = OpportunityRegistry(Path(tmp) / "opportunities.jsonl")
            bypass = make_record(
                status=OpportunityStatus.CLAIMED_OR_ENABLED_CONFIRMED,
            )
            with self.assertRaisesRegex(ValueError, "begin as DISCOVERED"):
                registry.upsert(bypass, now_ms=2_000)

    def test_registry_rejects_invalid_persisted_transition(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            registry = OpportunityRegistry(Path(tmp) / "opportunities.jsonl")
            record = make_record()
            registry.upsert(record, now_ms=2_000)
            with self.assertRaisesRegex(ValueError, "invalid persisted"):
                registry.upsert(
                    make_record(status=OpportunityStatus.CLAIMED_OR_ENABLED_CONFIRMED),
                    now_ms=2_000,
                )

    def test_malformed_jsonl_rows_are_ignored(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "opportunities.jsonl"
            path.write_text("{not-json}\n" + json.dumps(make_record().to_dict()) + "\n", encoding="utf-8")
            self.assertEqual(len(OpportunityRegistry(path).list_records()), 1)


if __name__ == "__main__":
    unittest.main()
