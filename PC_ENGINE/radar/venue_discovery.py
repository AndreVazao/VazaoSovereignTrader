from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
_MAX_CATALOGUE_BYTES = 1_000_000
_MAX_VENUES = 250


@dataclass(frozen=True)
class VenueProfile:
    venue_id: str
    display_name: str
    official_url: str
    api_docs_url: str
    ccxt_id: str | None
    lifecycle: str = "public_research_only"
    public_rest: bool = True
    public_websocket: str = "not_verified"
    private_account_access: str = "not_configured"
    jurisdiction_status: str = "unknown"
    source: str = "built_in_catalogue"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Initial entries are a starting catalogue, not a permanent venue allowlist.
# WebSocket coverage is deliberately conservative: only native collectors
# already present in this repository are marked implemented.
_BUILTIN: tuple[VenueProfile, ...] = (
    VenueProfile("binance", "Binance", "https://www.binance.com", "https://developers.binance.com/docs", "binance", public_websocket="native_trades_and_l2"),
    VenueProfile("coinbase", "Coinbase", "https://www.coinbase.com", "https://docs.cdp.coinbase.com", "coinbase", public_websocket="native_trades_and_l2"),
    VenueProfile("okx", "OKX", "https://www.okx.com", "https://www.okx.com/docs-v5/en/", "okx", public_websocket="native_trades_and_l2"),
    VenueProfile("bingx", "BingX", "https://bingx.com", "https://bingx-api.github.io/docs/", "bingx"),
    VenueProfile("bybit", "Bybit", "https://www.bybit.com", "https://bybit-exchange.github.io/docs/v5/intro", "bybit"),
    VenueProfile("bitget", "Bitget", "https://www.bitget.com", "https://www.bitget.com/api-doc/common/intro", "bitget"),
)


def _https_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError(f"{field}_invalid")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{field}_must_be_https")
    if parsed.fragment:
        raise ValueError(f"{field}_fragment_not_allowed")
    return value


def _validate_extension(item: Any) -> VenueProfile:
    if not isinstance(item, dict):
        raise ValueError("venue_entry_must_be_object")
    venue_id = item.get("venue_id")
    name = item.get("display_name")
    ccxt_id = item.get("ccxt_id")
    if not isinstance(venue_id, str) or not _ID_RE.fullmatch(venue_id):
        raise ValueError("venue_id_invalid")
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError("display_name_invalid")
    if ccxt_id is not None and (
        not isinstance(ccxt_id, str) or not _ID_RE.fullmatch(ccxt_id)
    ):
        raise ValueError("ccxt_id_invalid")
    return VenueProfile(
        venue_id=venue_id,
        display_name=name.strip(),
        official_url=_https_url(item.get("official_url"), "official_url"),
        api_docs_url=_https_url(item.get("api_docs_url"), "api_docs_url"),
        ccxt_id=ccxt_id,
        lifecycle="discovered_unverified",
        public_rest=False,
        public_websocket="not_verified",
        private_account_access="not_configured",
        jurisdiction_status="unknown",
        source="local_candidate_file",
    )


class VenueDiscoveryRegistry:
    """Extensible venue catalogue with public-only, fail-closed discovery.

    Catalogue membership never grants account access or financial capability.
    Local candidates remain unverified and cannot be treated as supported
    adapters until separate identity, API and jurisdiction checks pass.
    """

    def __init__(self, candidates_file: str | Path | None = None):
        self._venues: dict[str, VenueProfile] = {v.venue_id: v for v in _BUILTIN}
        if candidates_file is not None:
            self.load_candidates(candidates_file)

    def load_candidates(self, path: str | Path) -> int:
        candidate_path = Path(path)
        if not candidate_path.exists():
            return 0
        if candidate_path.is_symlink() or not candidate_path.is_file():
            raise ValueError("candidate_file_not_regular")
        if candidate_path.stat().st_size > _MAX_CATALOGUE_BYTES:
            raise ValueError("candidate_file_too_large")
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or len(payload) > _MAX_VENUES:
            raise ValueError("candidate_file_invalid_shape")
        additions: dict[str, VenueProfile] = {}
        for raw in payload:
            venue = _validate_extension(raw)
            if venue.venue_id in self._venues or venue.venue_id in additions:
                raise ValueError("duplicate_venue_id")
            additions[venue.venue_id] = venue
        if len(self._venues) + len(additions) > _MAX_VENUES:
            raise ValueError("venue_catalogue_limit_exceeded")
        self._venues.update(additions)
        return len(additions)

    def get(self, venue_id: str) -> VenueProfile | None:
        return self._venues.get(venue_id.lower())

    def list_venues(self) -> list[VenueProfile]:
        return sorted(self._venues.values(), key=lambda venue: venue.venue_id)

    def ccxt_candidates(self, installed_exchange_ids: list[str]) -> list[dict[str, str]]:
        """List installed CCXT venues not in the curated catalogue as unverified leads."""
        known = {v.ccxt_id for v in self._venues.values() if v.ccxt_id}
        result = []
        for raw_id in sorted(set(installed_exchange_ids)):
            if not isinstance(raw_id, str) or not _ID_RE.fullmatch(raw_id):
                continue
            if raw_id not in known:
                result.append({
                    "ccxt_id": raw_id,
                    "lifecycle": "discovered_unverified",
                    "next_step": "verify_official_identity_docs_jurisdiction_and_public_api",
                })
        return result
