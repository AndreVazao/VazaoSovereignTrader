import pytest

from PC_ENGINE.research.worker import ResearchWorker


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://127.0.0.1:8765/health",
    "http://localhost:8765/health",
])
def test_research_worker_rejects_non_public_urls(url):
    with pytest.raises(ValueError):
        ResearchWorker._validate_public_url(url)
