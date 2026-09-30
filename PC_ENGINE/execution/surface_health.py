from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ExecutionSurface(str, Enum):
    API = "API"
    WEB_BROWSER = "WEB_BROWSER"
    DESKTOP_APP = "DESKTOP_APP"
    ANDROID_APK = "ANDROID_APK"
    HUMAN = "HUMAN"


class SurfaceState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True)
class ExecutionSurfaceStatus:
    venue_id: str
    account_id: str
    surface: ExecutionSurface
    state: SurfaceState
    enabled: bool
    last_check_age_ms: int | None = None
    last_feedback_age_ms: int | None = None
    detail: str = ""
    paper_only: bool = True
    orders_submitted: bool = False
    execution_authorized: bool = False


def classify_surface(
    *,
    venue_id: str,
    account_id: str,
    surface: ExecutionSurface,
    enabled: bool,
    check_ok: bool | None,
    feedback_age_ms: int | None,
    stale_after_ms: int = 30_000,
    detail: str = "",
) -> ExecutionSurfaceStatus:
    """Classify transport health only.

    HEALTHY means that the transport is responding and feedback is fresh.
    It never means profitable, risk-approved or authorized to trade.
    """
    if not enabled:
        state = SurfaceState.NOT_CONFIGURED
    elif check_ok is False:
        state = SurfaceState.DOWN
    elif check_ok is None or feedback_age_ms is None:
        state = SurfaceState.DEGRADED
    elif feedback_age_ms > stale_after_ms:
        state = SurfaceState.DEGRADED
    else:
        state = SurfaceState.HEALTHY

    return ExecutionSurfaceStatus(
        venue_id=str(venue_id),
        account_id=str(account_id),
        surface=surface,
        state=state,
        enabled=bool(enabled),
        last_feedback_age_ms=feedback_age_ms,
        detail=str(detail),
    )


def snapshot(statuses: list[ExecutionSurfaceStatus]) -> dict[str, Any]:
    return {
        "operational_only": True,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "surfaces": [
            {**asdict(status), "surface": status.surface.value, "state": status.state.value}
            for status in statuses
        ],
    }
