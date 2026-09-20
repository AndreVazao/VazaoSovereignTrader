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
