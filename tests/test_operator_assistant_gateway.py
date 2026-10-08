from __future__ import annotations

from types import SimpleNamespace

from PC_ENGINE.api.assistant_gateway import OperatorAssistantGateway
from PC_ENGINE.research.inbox import TraderResearchInbox


class Principal:
    def __init__(self, *scopes):
        self.scopes = set(scopes)

    def has(self, scope):
        return scope in self.scopes


class Engine:
    mode = "PAPER"

    def __init__(self):
        self.calls = []
        self.status = "OFF"

    def snapshot(self):
        return {
            "status": self.status,
            "mode": self.mode,
            "balance": 1000.0,
            "equity": 1002.5,
            "drawdown_pct": 0.01,
        }

    def start(self):
        self.calls.append("start")
        self.status = "RUNNING"

    def pause(self, value):
        self.calls.append(("pause", value))
        if value:
            self.status = "PAUSED"
            return True
        self.status = "RUNNING"
        return True

    def stop(self):
        self.calls.append("stop")
        self.status = "OFF"


def test_research_message_is_queued_for_paired_operator(tmp_path):
    engine = Engine()
    research = TraderResearchInbox(tmp_path)
    gateway = OperatorAssistantGateway(engine, research)
    result = gateway.handle(
        "Investiga este link https://example.com e vê se há algo útil.",
        Principal("read_private_state", "submit_research"),
    )
    assert result["ok"] is True
    assert result["intent"] == "RESEARCH"
    assert result["status"] == "QUEUED"
    assert research.snapshot()["pending"] == 1


def test_research_requires_dedicated_mobile_scope(tmp_path):
    gateway = OperatorAssistantGateway(Engine(), TraderResearchInbox(tmp_path))
    try:
        gateway.handle("Investiga isto https://example.com", Principal("read_private_state"))
    except PermissionError as exc:
        assert str(exc) == "scope_required:submit_research"
    else:
        raise AssertionError("research scope bypassed")


def test_real_language_is_never_authorization(tmp_path):
    result = OperatorAssistantGateway(Engine(), TraderResearchInbox(tmp_path)).handle(
        "Executa isto em REAL.",
        Principal("read_private_state", "trade_paper", "submit_research"),
    )
    assert result["intent"] == "REAL_BLOCKED"
    assert result["execution_authorized"] is False


def test_paper_control_is_routed_to_existing_engine_boundary(tmp_path):
    engine = Engine()
    gateway = OperatorAssistantGateway(engine, TraderResearchInbox(tmp_path))
    result = gateway.handle("iniciar", Principal("read_private_state", "trade_paper"))
    assert result["intent"] == "START"
    assert engine.calls == ["start"]


def test_status_is_read_only(tmp_path):
    engine = Engine()
    result = OperatorAssistantGateway(engine, TraderResearchInbox(tmp_path)).handle(
        "Qual é o estado e o saldo?",
        Principal("read_private_state"),
    )
    assert result["intent"] == "STATUS"
    assert result["data"]["balance"] == 1000.0
    assert engine.calls == []
