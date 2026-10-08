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

    def __init__(self, engine, research: TraderResearchInbox):
        self.engine = engine
        self.research = research

    @staticmethod
    def _clean(message: str) -> str:
        return " ".join(str(message or "").split()).strip()

    @staticmethod
    def _has_url(message: str) -> bool:
        return bool(re.search(r"https?://\S+", message, re.I))

    def handle(self, message: str, principal: Any) -> dict[str, Any]:
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
            item = self.research.submit(text)
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
