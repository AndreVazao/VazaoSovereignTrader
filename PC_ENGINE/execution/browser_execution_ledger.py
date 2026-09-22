from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class BrowserExecutionRecord:
    idempotency_key: str
    owner_id: str
    venue_id: str
    account_id: str
    symbol: str
    action: str
    quantity: float
    state: str
    external_id: str | None
    page_fingerprint: str
    context_fingerprint: str
    recorded_at_ms: int


class BrowserExecutionLedger:
    """Append-only, owner-private browser execution journal."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def latest(self, idempotency_key: str) -> BrowserExecutionRecord | None:
        if not self.path.exists():
            return None
        found = None
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = BrowserExecutionRecord(**json.loads(line))
                except (json.JSONDecodeError, TypeError):
                    continue
                if item.idempotency_key == idempotency_key:
                    found = item
        return found

    def records(self) -> list[BrowserExecutionRecord]:
        if not self.path.exists():
            return []
        latest: dict[str, BrowserExecutionRecord] = {}
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = BrowserExecutionRecord(**json.loads(line))
                except (json.JSONDecodeError, TypeError):
                    continue
                latest[item.idempotency_key] = item
        return list(latest.values())

    def pending_submissions(self) -> list[BrowserExecutionRecord]:
        """Return browser actions that may have reached the exchange.

        SUBMISSION_AUTHORIZED is included because a browser click can succeed
        while the process loses the response before SUBMITTED is appended.
        Recovery must then resolve the durable client id instead of clicking
        again.
        """
        return [
            item for item in self.records()
            if item.state in {"SUBMISSION_AUTHORIZED", "SUBMITTED"}
        ]

    def append(self, *, intent, state: str, external_id: str | None, page_fingerprint: str, context_fingerprint: str) -> BrowserExecutionRecord:
        if not intent.idempotency_key:
            raise ValueError("idempotency_key is required")
        item = BrowserExecutionRecord(
            idempotency_key=intent.idempotency_key,
            owner_id=intent.owner_id,
            venue_id=intent.venue_id,
            account_id=intent.account_id,
            symbol=intent.symbol,
            action=intent.action,
            quantity=float(intent.quantity),
            state=str(state),
            external_id=external_id,
            page_fingerprint=page_fingerprint,
            context_fingerprint=context_fingerprint,
            recorded_at_ms=int(time.time() * 1000),
            stop_pct=None if getattr(intent, "stop_pct", None) is None else float(intent.stop_pct),
            take_profit_pct=None if getattr(intent, "take_profit_pct", None) is None else float(intent.take_profit_pct),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
        return item
