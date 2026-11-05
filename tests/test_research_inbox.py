from __future__ import annotations

import threading
import time

from PC_ENGINE.research.inbox import TraderResearchInbox


def test_research_submit_extracts_public_urls(tmp_path):
    inbox = TraderResearchInbox(str(tmp_path))
    item = inbox.submit("Analisa isto https://example.com/test e também https://example.org")
    assert item.status == "PENDING"
    assert item.urls == ["https://example.com/test", "https://example.org"]
    snap = inbox.snapshot()
    assert snap["pending"] == 1
    assert snap["requests"][0]["message"].startswith("Analisa isto")


def test_research_rejects_empty_message(tmp_path):
    inbox = TraderResearchInbox(str(tmp_path))
    try:
        inbox.submit("   ")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert str(exc) == "research_message_required"


def test_claim_is_exclusive_and_completion_requires_owner(tmp_path):
    inbox = TraderResearchInbox(str(tmp_path))
    request = inbox.submit("Investigar spread")
    first = inbox.claim_next("worker-a", lease_seconds=60)
    second = inbox.claim_next("worker-b", lease_seconds=60)
    assert first.request_id == request.request_id
    assert second is None
    assert not inbox.complete(request.request_id, "worker-b", status="COMPLETED", result="wrong owner")
    assert inbox.complete(request.request_id, "worker-a", status="COMPLETED", result="done")
    assert inbox.snapshot()["completed"] == 1


def test_expired_lease_is_reclaimed_and_attempt_count_increments(tmp_path):
    inbox = TraderResearchInbox(str(tmp_path))
    request = inbox.submit("Investigar liquidez")
    claimed = inbox.claim_next("worker-crashed", lease_seconds=30)
    assert claimed.attempt_count == 1
    # Simulate expiry without sleeping.
    claimed.lease_expires_at = time.time() - 1
    with inbox._file_lock():
        inbox._append_unlocked(claimed)
    recovered = inbox.claim_next("worker-restarted", lease_seconds=60)
    assert recovered.request_id == request.request_id
    assert recovered.attempt_count == 2
    assert recovered.lease_owner == "worker-restarted"


def test_expired_lease_fails_closed_after_attempt_limit(tmp_path):
    inbox = TraderResearchInbox(str(tmp_path))
    request = inbox.submit("Investigar volatilidade")
    claimed = inbox.claim_next("worker-a", lease_seconds=30, max_attempts=1)
    claimed.lease_expires_at = time.time() - 1
    with inbox._file_lock():
        inbox._append_unlocked(claimed)
    assert inbox.claim_next("worker-b", max_attempts=1) is None
    snapshot = inbox.snapshot()
    assert snapshot["failed"] == 1
    assert snapshot["requests"][0]["status"] == "FAILED"


def test_only_one_worker_claims_a_request_across_threads(tmp_path):
    inbox_a = TraderResearchInbox(str(tmp_path))
    inbox_b = TraderResearchInbox(str(tmp_path))
    inbox_a.submit("Investigar microestrutura")
    barrier = threading.Barrier(2)
    claims = []

    def claim(inbox, owner):
        barrier.wait()
        claims.append(inbox.claim_next(owner))

    a = threading.Thread(target=claim, args=(inbox_a, "a"))
    b = threading.Thread(target=claim, args=(inbox_b, "b"))
    a.start()
    b.start()
    a.join()
    b.join()
    assert sum(item is not None for item in claims) == 1
