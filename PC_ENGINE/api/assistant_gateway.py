from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from PC_ENGINE.research.inbox import TraderResearchInbox


class OperatorAssistantGateway:
    """Small deterministic command router for the mobile conversational cockpit.

    This is an operator UX layer, not an autonomous trading brain. It may route
    only to existing authenticated PAPER/read-only surfaces. REAL requests are
    explicitly refused and never converted into authorization.
    """

    _REAL_RE = re.compile(r"\b(real|live|dinheiro real|capital real|ordem real|executa real)\b", re.I)
    _RESEARCH_RE = re.compile(
        r"\b(investiga|investigar|pesquisa|pesquisar|analisa|analisar|estuda|estudar|procura|procurar|research|investigate|analyse|analyze)\b",
        re.I,
    )
    _STATUS_RE = re.compile(
        r"\b(estado|status|como está|como esta|saldo|equity|risco|drawdown|saúde|saude|diagnóstico|diagnostico)\b",
        re.I,
    )

    def __init__(self, engine, research: TraderResearchInbox, department_readers=None):
        self.engine = engine
        self.research = research
        self.department_readers = dict(department_readers or {})

    @staticmethod
    def _clean(message: str) -> str:
        return " ".join(str(message or "").split()).strip()

    @staticmethod
    def _has_url(message: str) -> bool:
        return bool(re.search(r"https?://\S+", message, re.I))

    DEPARTMENTS = {
        "brain": "Cérebro / CEO",
        "markets": "Exchanges",
        "radar": "Market Radar",
        "research": "Investigação",
        "paper": "Laboratório PAPER",
        "risk": "Controlo de risco",
        "recovery": "Recuperação",
        "audit": "Auditoria",
        "human": "Intervenção humana",
    }

    def handle(self, message: str, principal: Any, department: str = "brain") -> dict[str, Any]:
        department = str(department or "brain").strip().lower()
        if department not in self.DEPARTMENTS:
            raise ValueError("assistant_department_invalid")
        result = self._handle(message, principal, department)
        result["department"] = department
        result["department_label"] = self.DEPARTMENTS[department]
        return result

    def _handle(self, message: str, principal: Any, department: str) -> dict[str, Any]:
        text = self._clean(message)
        if not text:
            raise ValueError("assistant_message_required")

        if self._REAL_RE.search(text):
            return {
                "ok": False,
                "intent": "REAL_BLOCKED",
                "status": "BLOCKED",
                "reply": (
                    "Pedido REAL recusado nesta interface. A conversa nunca cria autorização REAL. "
                    "Se precisares de REAL, usa exclusivamente o fluxo protegido de autorização humana."
                ),
                "paper_only": True,
                "execution_authorized": False,
            }

        lower = text.lower()
        if self._STATUS_RE.search(text) and not self._RESEARCH_RE.search(text):
            if department != "brain":
                return self._department_status(department)
            snapshot = self.engine.snapshot()
            return {
                "ok": True,
                "intent": "STATUS",
                "status": "COMPLETED",
                "reply": self._status_reply(snapshot),
                "data": {
                    "status": snapshot.get("status"),
                    "mode": snapshot.get("mode"),
                    "balance": snapshot.get("balance"),
                    "equity": snapshot.get("equity"),
                    "drawdown_pct": snapshot.get("drawdown_pct"),
                },
                "paper_only": True,
                "execution_authorized": False,
            }

        if lower in {"iniciar", "inicia", "ligar", "começar", "comecar", "start"}:
            self._require(principal, "trade_paper")
            self.engine.start()
            return self._ack("START", "Motor iniciado através do caminho PAPER protegido.")

        if lower in {"pausar", "pausa", "pause"}:
            self._require(principal, "trade_paper")
            self.engine.pause(True)
            return self._ack("PAUSE", "Motor pausado.")

        if lower in {"retomar", "retoma", "resume"}:
            self._require(principal, "trade_paper")
            if not self.engine.pause(False):
                return {
                    "ok": False,
                    "intent": "RESUME",
                    "status": "BLOCKED",
                    "reply": "O motor está em SAFE_MODE. A recuperação exige o fluxo explícito de recuperação segura.",
                    "paper_only": True,
                    "execution_authorized": False,
                }
            return self._ack("RESUME", "Motor retomado.")

        if lower in {"parar", "para", "stop"}:
            self._require(principal, "trade_paper")
            self.engine.stop()
            return self._ack("STOP", "Motor parado.")

        if self._RESEARCH_RE.search(text) or self._has_url(text):
            self._require(principal, "submit_research")
            routed_text = text if department == "brain" else f"[Departamento solicitado: {self.DEPARTMENTS[department]}] {text}"
            item = self.research.submit(routed_text)
            return {
                "ok": True,
                "intent": "RESEARCH",
                "status": "QUEUED",
                "reply": (
                    f"Recebi o pedido e coloquei-o na fila de investigação ({item.request_id[:8]}). "
                    "O worker vai analisar as fontes públicas permitidas e medir a hipótese contra os dados próprios."
                ),
                "request": asdict(item),
                "paper_only": True,
                "execution_authorized": False,
            }

        if department != "brain":
            if department in self.department_readers:
                return self._department_status(department)
            return {
                "ok": True,
                "intent": "DEPARTMENT_NOT_CONNECTED",
                "status": "NOT_CONNECTED",
                "reply": (
                    f"O contexto selecionado é {self.DEPARTMENTS[department]}, mas ainda não existe "
                    "um handler de leitura ligado a este departamento. Não vou fingir que uma equipa "
                    "autónoma respondeu. Os pedidos de investigação usam a fila comum."
                ),
                "paper_only": True,
                "execution_authorized": False,
            }

        return {
            "ok": True,
            "intent": "CHAT",
            "status": "COMPLETED",
            "reply": (
                "Estou ligado ao cérebro do Sovereign Trader. Posso consultar o estado, "
                "executar controlos PAPER protegidos, investigar links/temas e tratar intervenções humanas. "
                "Pedidos REAL continuam bloqueados nesta conversa."
            ),
            "paper_only": True,
            "execution_authorized": False,
        }

    def _department_status(self, department: str) -> dict[str, Any]:
        reader = self.department_readers.get(department)
        if reader is None:
            return {
                "ok": True,
                "intent": "DEPARTMENT_NOT_CONNECTED",
                "status": "NOT_CONNECTED",
                "reply": f"Não existe handler de leitura ligado a {self.DEPARTMENTS[department]}.",
                "paper_only": True,
                "execution_authorized": False,
            }
        try:
            raw = reader()
        except Exception as exc:
            return {
                "ok": False,
                "intent": "DEPARTMENT_STATUS",
                "status": "UNAVAILABLE",
                "reply": f"A leitura de {self.DEPARTMENTS[department]} falhou ({type(exc).__name__}). Não foi executada nenhuma ação.",
                "paper_only": True,
                "execution_authorized": False,
            }
        payload = raw if isinstance(raw, dict) else {}
        data: dict[str, Any] = {"department": department}
        if department == "markets":
            venues = payload.get("venues", [])
            venues = venues if isinstance(venues, list) else []
            counts = payload.get("counts", {})
            counts = counts if isinstance(counts, dict) else {}
            data["counts"] = {key: int(counts.get(key, 0) or 0) for key in ("GREEN", "YELLOW", "RED")}
            data["venues"] = [
                {
                    "exchange": str(item.get("exchange", item.get("venue", "unknown"))),
                    "status": str(item.get("status", "UNKNOWN")),
                    "label": str(item.get("label", "")),
                    "age_ms": item.get("age_ms"),
                    "sample_count": item.get("sample_count"),
                }
                for item in venues if isinstance(item, dict)
            ]
            reply = (
                f"Saúde operacional: {len(data['venues'])} venues observadas; "
                f"GREEN {data['counts']['GREEN']}, YELLOW {data['counts']['YELLOW']}, RED {data['counts']['RED']}. "
                "Isto mede recência/amostras, não rentabilidade nem autorização de execução."
            )
        elif department == "research":
            data.update({key: int(payload.get(key, 0) or 0) for key in ("pending", "active", "completed", "discarded")})
            reply = (
                f"Fila de investigação: {data['pending']} pendentes, {data['active']} em curso, "
                f"{data['completed']} concluídas e {data['discarded']} descartadas."
            )
        elif department == "human":
            data.update({key: int(payload.get(key, 0) or 0) for key in ("pending", "responded_waiting_pc", "applied")})
            reply = (
                f"Intervenção humana: {data['pending']} pendentes, {data['responded_waiting_pc']} respostas à espera do PC "
                f"e {data['applied']} aplicadas. A interface não preenche segredos nem contorna MFA/CAPTCHA."
            )
        elif department == "audit":
            for key in ("records", "eligible_records", "rejected_records", "eligibility_ratio", "latest_created_at_ms"):
                if key in payload:
                    data[key] = payload[key]
            reply = (
                f"Auditoria PAPER: {data.get('records', 0)} registos, "
                f"{data.get('eligible_records', 0)} elegíveis e {data.get('rejected_records', 0)} rejeitados. "
                "A elegibilidade histórica não autoriza execução REAL."
            )
        else:
            allowed = (
                "status", "state", "ok", "stale", "health_age_ms", "timestamp_ms",
                "score", "ready", "passed", "failed", "samples", "sample_count",
                "pass_ratio", "min_pass_ratio", "recent_pass_ratio", "total", "count",
                "reason", "recovery_state", "safe_mode", "unresolved", "pending",
                "eligible", "eligible_records", "rejected_records",
            )
            for key in allowed:
                value = payload.get(key)
                if isinstance(value, (str, int, float, bool)) or value is None:
                    if key in payload:
                        data[key] = value
            summary = ", ".join(f"{key}={value}" for key, value in data.items() if key != "department")
            reply = f"Leitura de {self.DEPARTMENTS[department]} (dados reais do backend): {summary or 'sem campos de resumo disponíveis'}. Isto não é uma resposta de agente autónomo."
        return {
            "ok": True,
            "intent": "DEPARTMENT_STATUS",
            "status": "COMPLETED",
            "reply": reply,
            "data": data,
            "paper_only": True,
            "execution_authorized": False,
        }

    @staticmethod
    def _require(principal: Any, scope: str) -> None:
        if not principal.has(scope):
            raise PermissionError(f"scope_required:{scope}")

    @staticmethod
    def _ack(intent: str, reply: str) -> dict[str, Any]:
        return {
            "ok": True,
            "intent": intent,
            "status": "COMPLETED",
            "reply": reply,
            "paper_only": True,
            "execution_authorized": False,
        }

    @staticmethod
    def _status_reply(snapshot: dict[str, Any]) -> str:
        status = snapshot.get("status", "---")
        mode = snapshot.get("mode", "---")
        balance = snapshot.get("balance", 0)
        equity = snapshot.get("equity", 0)
        dd = float(snapshot.get("drawdown_pct", 0) or 0) * 100
        return (
            f"Estado: {status} · Modo: {mode} · Saldo: {balance:.2f} · "
            f"Equity: {equity:.2f} · Drawdown: {dd:.2f}%. "
            "Esta leitura não autoriza execução REAL."
        )
