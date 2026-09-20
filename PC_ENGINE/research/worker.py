from __future__ import annotations

import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from html import unescape
from pathlib import Path

from PC_ENGINE.research.inbox import TraderResearchInbox
from PC_ENGINE.research.knowledge import ResearchKnowledge
from PC_ENGINE.research.evaluator import ResearchOwnDataEvaluator


class ResearchWorker:
    """Processes research requests using permitted public HTTP pages.

    It deliberately performs no login, CAPTCHA solving, anti-bot bypass or trading.
    The output is evidence/hypotheses only.
    """

    def __init__(self, data_dir: str = "PC_ENGINE/data/research", timeout_seconds: float = 8.0):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.inbox = TraderResearchInbox(data_dir)
        self.knowledge = ResearchKnowledge(data_dir)
        self.evaluator = ResearchOwnDataEvaluator(
            replay_path="PC_ENGINE/data/replay/l2_temporal_replay.json",
            oos_path="PC_ENGINE/data/radar/l2_oos_validation.json",
        )
        self.timeout = float(timeout_seconds)

    def run_forever(self, stop_event, interval_seconds: float = 2.0) -> None:
        """Process research in its own worker thread without blocking market cycles."""
        interval = max(0.25, float(interval_seconds))
        while not stop_event.is_set():
            try:
                self.process_pending(max_items=1)
            except Exception:
                # Research is non-critical. A broken source must never stop the trader.
                pass
            stop_event.wait(interval)

    def process_pending(self, max_items: int = 1) -> dict:
        items = self.inbox._latest()
        processed = 0
        for item in sorted(items.values(), key=lambda x: x.created_at):
            if item.status != "PENDING" or processed >= max_items:
                continue
            processed += 1
            item.status = "IN_PROGRESS"
            item.updated_at = time.time()
            self.inbox._append(item)
            try:
                result = self._process(item.message, item.urls)
                item.result = result["summary"]
                item.status = "COMPLETED" if result["interesting"] else "DISCARDED"
                evaluation = self.evaluator.evaluate(item.message)
                item.result = f'{result["summary"]} {evaluation["summary"]}'
                final_status = evaluation["status"]
                evidence_available = final_status != "INSUFFICIENT_DATA"
                item.status = "COMPLETED" if (result["interesting"] or evidence_available) else "DISCARDED"
                self.knowledge.record(
                    title=f"Research: {item.message[:100]}",
                    category=result["category"],
                    status="validating" if final_status == "OOS_VALIDATION_CANDIDATE" else (
                        "hypothesis" if (result["interesting"] or evidence_available) else "failed"
                    ),
                    evidence=f'{result["summary"]} {evaluation["summary"]}',
                    source_urls=item.urls + evaluation["data_sources"],
                    metrics={
                        "pages_read": result["pages_read"],
                        **evaluation["metrics"],
                        "evidence_ids": evaluation["evidence_ids"],
                    },
                    tags=["research-worker", "own-data-evaluation"],
                    hypothesis_id=item.request_id,
                )
            except Exception as exc:
                item.status = "DISCARDED"
                item.result = f"Pesquisa interrompida: {type(exc).__name__}"
            item.updated_at = time.time()
            self.inbox._append(item)
        return {"processed": processed, "queue": self.inbox.snapshot()}

    def _process(self, message: str, urls: list[str]) -> dict:
        pages = []
        for url in urls[:5]:
            text = self._fetch_public_page(url)
            if text:
                pages.append((url, text))
        if not pages:
            if not urls:
                return {
                    "interesting": True,
                    "category": "market_pattern",
                    "summary": "Hipótese interna autónoma; não depende de fonte web. Será medida apenas contra os dados próprios disponíveis.",
                    "pages_read": 0,
                }
            return {
                "interesting": False,
                "category": "failed_hypothesis",
                "summary": "Nenhuma fonte pública acessível foi encontrada; hipótese descartada.",
                "pages_read": 0,
            }

        corpus = " ".join(text for _, text in pages)
        terms = re.findall(r"\b(?:lead|lag|latency|liquidity|spread|volatility|arbitrage|momentum|mean reversion|microstructure|execution)\b", corpus.lower())
        unique_terms = sorted(set(terms))
        interesting = len(unique_terms) >= 2 or len(corpus) >= 1500
        category = "lead_lag" if any(x in unique_terms for x in ("lead", "lag", "latency")) else "market_pattern"
        summary = (
            f"Fontes públicas analisadas: {len(pages)}. "
            f"Conceitos relevantes encontrados: {', '.join(unique_terms[:8]) or 'nenhum'}. "
            f"Esta é evidência de investigação, não uma regra de trading; qualquer hipótese "
            f"terá de ser medida nos dados próprios e passar PAPER/OOS."
        )
        return {"interesting": interesting, "category": category, "summary": summary, "pages_read": len(pages)}

    def _fetch_public_page(self, url: str) -> str:
        req = Request(url, headers={"User-Agent": "VazaoSovereignTrader-Research/1.0"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return ""
                raw = response.read(1_000_000).decode("utf-8", errors="ignore")
        except (HTTPError, URLError, TimeoutError, ValueError):
            return ""
        raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", raw)
        raw = re.sub(r"(?s)<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", unescape(raw)).strip()
