from __future__ import annotations

from PC_ENGINE.research.local_context_assistant import LocalContextAssistant


class Lease:
    def __init__(self):
        self.released = False

    def release(self):
        self.released = True


class Supervisor:
    def __init__(self):
        self.lease = Lease()
        self.calls = []

    def acquire(self, name):
        self.calls.append(name)
        return self.lease


def test_missing_local_model_returns_none_and_releases_service_lease():
    supervisor = Supervisor()
    assistant = LocalContextAssistant(supervisor, model="not-installed")
    assistant._choose_model = lambda: None
    assert assistant.interpret("Please assess this strategy idea") is None
    assert assistant.last_status == "NO_LOCAL_MODEL"
    assert supervisor.calls == ["ollama"]
    assert supervisor.lease.released is True


def test_local_context_result_is_bounded_and_advisory():
    supervisor = Supervisor()
    assistant = LocalContextAssistant(supervisor, model="local-model")
    assistant._choose_model = lambda: "local-model"
    seen = {}

    def post(path, payload):
        seen["path"] = path
        seen["payload"] = payload
        return {"response": "A" * 7000}

    assistant._post_json = post
    result = assistant.interpret("Owner asks to assess a link", source_text="source" * 2000)
    assert result is not None and len(result) == 6000
    assert seen["path"] == "/api/generate"
    assert seen["payload"]["keep_alive"] == "0"
    assert len(seen["payload"]["prompt"]) < 17000
    assert "do not execute trades" in seen["payload"]["prompt"]
    assert assistant.last_status == "OK_LOCAL_ADVISORY"
    assert supervisor.lease.released is True


def test_service_failure_falls_back_without_propagating():
    supervisor = Supervisor()
    supervisor.acquire = lambda _name: (_ for _ in ()).throw(RuntimeError("offline"))
    assistant = LocalContextAssistant(supervisor)
    assert assistant.interpret("check context") is None
    assert assistant.last_status == "LOCAL_AI_UNAVAILABLE"
