from __future__ import annotations

import time
from pathlib import Path
from PC_ENGINE.research.inbox import TraderResearchInbox
from PC_ENGINE.research.knowledge import ResearchKnowledge


class AutonomousResearchWorker:
    """Turns internal observations into research hypotheses without operator input.

    It does not trade. It only creates deduplicated research tasks for patterns
    that deserve measurement. External-source research can consume the same queue.
    """

    def __init__(self, data_dir: str = "PC_ENGINE/data/research"):
        self.inbox = TraderResearchInbox(data_dir)
        self.knowledge = ResearchKnowledge(data_dir)
        self.state_path = Path(data_dir) / "autonomous_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_emit: dict[str, float] = {}
        self._load()

    def observe(self, symbol: str, score: float, regime: str, opportunity: dict | None = None) -> bool:
        score = float(score)
        key = f"{symbol}:{regime}"
        now = time.time()
        # Avoid filling the queue with the same observation every cycle.
        if score < 70.0 or now - self._last_emit.get(key, 0.0) < 3600:
            return False
        opp = opportunity or {}
        message = (
            f"Investigar autonomamente {symbol} no regime {regime}. "
            f"O score observado foi {score:.2f}. "
            f"Verificar se existe um padrão, lead/lag, microestrutura ou condição "
            f"de execução repetível e mensurável. Usar apenas evidência pública/permitted; "
            f"testar custos, liquidez e estabilidade antes de promover a hipótese."
        )
        request = self.inbox.submit(message)
        self.knowledge.record(
            title=f"Autonomous research: {symbol} {regime}",
            category="market_pattern",
            status="hypothesis",
            evidence=f"Internal observation score={score:.2f}; regime={regime}",
            tags=[symbol, regime.lower(), "autonomous"],
            hypothesis_id=request.request_id,
        )
        self._last_emit[key] = now
        self._save()
        return True

    def snapshot(self) -> dict:
        return {
            "enabled": True,
            "last_emissions": len(self._last_emit),
            "queue": self.inbox.snapshot(),
            "knowledge": self.knowledge.snapshot(),
        }

    def _load(self) -> None:
        try:
            import json
            self._last_emit = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            self._last_emit = {}

    def _save(self) -> None:
        import json
        self.state_path.write_text(json.dumps(self._last_emit), encoding="utf-8")
