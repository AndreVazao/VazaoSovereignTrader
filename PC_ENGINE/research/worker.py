from __future__ import annotations

import ipaddress
import re
import socket
import time
import threading
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from html import unescape
from pathlib import Path

from PC_ENGINE.research.inbox import TraderResearchInbox
from PC_ENGINE.research.knowledge import ResearchKnowledge
from PC_ENGINE.research.evaluator import ResearchOwnDataEvaluator
from PC_ENGINE.research.local_context_assistant import create_local_context_assistant


class ResearchWorker:
    """Processes leased research requests using permitted public HTTP pages.

    It deliberately performs no login, CAPTCHA solving, anti-bot bypass or trading.
    The output is evidence/hypotheses only.
    """

    def __init__(
        self,
        data_dir: str = "PC_ENGINE/data/research",
        timeout_seconds: float = 8.0,
        replay_path: str = "PC_ENGINE/data/replay/l2_temporal_replay.json",
        oos_path: str = "PC_ENGINE/data/radar/l2_oos_validation.json",
    ):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.inbox = TraderResearchInbox(data_dir)
        self.knowledge = ResearchKnowledge(data_dir)
        self.evaluator = ResearchOwnDataEvaluator(replay_path=replay_path, oos_path=oos_path)
        self.context_assistant = create_local_context_assistant()
        self.timeout = float(timeout_seconds)
        self.lease_owner = f"{socket.gethostname()}:{os_getpid()}:{uuid.uuid4().hex}"
        self.lease_seconds = 300.0
        self.max_attempts = 3
        self._supervision_lock = threading.Lock()
        self._heartbeat_ts = 0.0
        self._last_success_ts = 0.0
        self._last_error_type = ""
        self._iterations = 0

    def supervision_snapshot(self) -> dict:
        with self._supervision_lock:
            return {
                "heartbeat_ts": self._heartbeat_ts,
                "last_success_ts": self._last_success_ts,
                "last_error_type": self._last_error_type,
                "iterations": self._iterations,
            }

    def run_forever(self, stop_event, interval_seconds: float = 2.0) -> None:
        interval = max(0.25, float(interval_seconds))
        while not stop_event.is_set():
            with self._supervision_lock:
                self._heartbeat_ts = time.time()
                self._iterations += 1
            try:
                self.process_pending(max_items=1)
                with self._supervision_lock:
                    self._last_success_ts = time.time()
                    self._last_error_type = ""
            except Exception as exc:
                with self._supervision_lock:
                    self._last_error_type = type(exc).__name__
            finally:
                with self._supervision_lock:
                    self._heartbeat_ts = time.time()
            stop_event.wait(interval)

    def process_pending(self, max_items: int = 1) -> dict:
        processed = 0
        for _ in range(max(0, int(max_items))):
            item = self.inbox.claim_next(
                self.lease_owner, lease_seconds=self.lease_seconds, max_attempts=self.max_attempts
            )
            if item is None:
                break
            processed += 1
            lease_stop = threading.Event()
            lease_thread = threading.Thread(
                target=self._renew_lease_while_processing,
                args=(item.request_id, lease_stop),
                name="vst-research-lease-heartbeat",
                daemon=True,
            )
            lease_thread.start()
            try:
                result = self._process(item.message, item.urls)
                if self.context_assistant is not None and result.get("pages_read", 0) > 0:
                    try:
                        interpretation = self.context_assistant.interpret(
                            item.message, source_text=result.get("source_excerpt", "")
                        )
                    except Exception:
                        interpretation = None
                    if interpretation:
                        result["summary"] += " Interpretação local advisory (não validada): " + interpretation[:3_000]
                evaluation = self.evaluator.evaluate(item.message)
                summary = f'{result["summary"]} {evaluation["summary"]}'
                final_status = evaluation["status"]
                evidence_available = final_status != "INSUFFICIENT_DATA"
                terminal_status = "COMPLETED" if (result["interesting"] or evidence_available) else "DISCARDED"
                if not self.knowledge.has_hypothesis(item.request_id):
                    self.knowledge.record(
                        title=f"Research: {item.message[:100]}",
                        category=result["category"],
                        status="validating" if final_status == "OOS_VALIDATION_CANDIDATE" else (
                            "hypothesis" if (result["interesting"] or evidence_available) else "failed"
                        ),
                        evidence=summary,
                        source_urls=item.urls + evaluation["data_sources"],
                        metrics={
                            "pages_read": result["pages_read"],
                            **evaluation["metrics"],
                            "evidence_ids": evaluation["evidence_ids"],
                        },
                        tags=["research-worker", "own-data-evaluation"],
                        hypothesis_id=item.request_id,
                    )
                if not self.inbox.complete(
                    item.request_id, self.lease_owner, status=terminal_status, result=summary
                ):
                    # Lease ownership was lost; a later claimant can safely retry.
                    raise RuntimeError("research_lease_lost_before_completion")
            except Exception as exc:
                self.inbox.release(
                    item.request_id, self.lease_owner, error_type=type(exc).__name__,
                    max_attempts=self.max_attempts,
                )
                raise
            finally:
                lease_stop.set()
                lease_thread.join(timeout=2.0)
        return {"processed": processed, "queue": self.inbox.snapshot()}

    def _renew_lease_while_processing(self, request_id: str, stop_event: threading.Event) -> None:
        # Keep long local-model interpretation/evaluation from expiring a live claim.
        while not stop_event.wait(30.0):
            if not self.inbox.renew_lease(
                request_id, self.lease_owner, lease_seconds=self.lease_seconds
            ):
                return

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
                    "source_excerpt": "",
                }
            return {
                "interesting": False,
                "category": "failed_hypothesis",
                "summary": "Nenhuma fonte pública acessível foi encontrada; hipótese descartada.",
                "pages_read": 0,
                "source_excerpt": "",
            }
        corpus = " ".join(text for _, text in pages)
        terms = re.findall(r"\b(?:lead|lag|latency|liquidity|spread|volatility|arbitrage|momentum|mean reversion|microstructure|execution)\b", corpus.lower())
        unique_terms = sorted(set(terms))
        interesting = len(unique_terms) >= 2 or len(corpus) >= 1500
        category = "lead_lag" if any(x in unique_terms for x in ("lead", "lag", "latency")) else "market_pattern"
        summary = (
            f"Fontes públicas analisadas: {len(pages)}. "
            f"Conceitos relevantes encontrados: {', '.join(unique_terms[:8]) or 'nenhum'}. "
            "Esta é evidência de investigação, não uma regra de trading; qualquer hipótese "
            "terá de ser medida nos dados próprios e passar PAPER/OOS."
        )
        return {
            "interesting": interesting,
            "category": category,
            "summary": summary,
            "pages_read": len(pages),
            "source_excerpt": corpus[:8_000],
        }

    @staticmethod
    def _validate_public_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("only public http/https URLs are allowed")
        if parsed.username or parsed.password:
            raise ValueError("URLs with embedded credentials are not allowed")
        host = parsed.hostname
        try:
            addresses = {
                info[4][0]
                for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            raise ValueError("host resolution failed") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                raise ValueError("private or non-public destination blocked")

    def _fetch_public_page(self, url: str) -> str:
        try:
            self._validate_public_url(url)
        except ValueError:
            return ""
        class SafeRedirectHandler(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                ResearchWorker._validate_public_url(newurl)
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        req = Request(url, headers={"User-Agent": "VazaoSovereignTrader-Research/1.0"})
        try:
            with build_opener(SafeRedirectHandler()).open(req, timeout=self.timeout) as response:
                self._validate_public_url(response.geturl())
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return ""
                raw = response.read(1_000_000).decode("utf-8", errors="ignore")
        except (HTTPError, URLError, TimeoutError, ValueError):
            return ""
        raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", raw)
        raw = re.sub(r"(?s)<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", unescape(raw)).strip()


def os_getpid() -> int:
    import os
    return os.getpid()
