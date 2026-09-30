from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

class Surface(str, Enum):
    WEB_BROWSER = "WEB_BROWSER"
    DESKTOP_APP = "DESKTOP_APP"
    ANDROID_APK = "ANDROID_APK"

class ActionKind(str, Enum):
    CONNECT = "CONNECT"
    OBSERVE = "OBSERVE"
    BUY = "BUY"
    SELL = "SELL"
    CANCEL = "CANCEL"

@dataclass(frozen=True)
class SurfaceFeedback:
    request_id: str
    surface: Surface
    venue_id: str
    state: str
    acknowledged: bool
    observed_at_ms: int
    detail: str = ""
    order_reference: str | None = None

@dataclass(frozen=True)
class SurfaceAction:
    request_id: str
    venue_id: str
    surface: Surface
    action: ActionKind
    paper_only: bool = True

class ExecutionSurfaceAdapter(Protocol):
    surface: Surface
    def probe(self) -> SurfaceFeedback: ...
    def observe(self) -> SurfaceFeedback: ...
    def execute(self, action: SurfaceAction) -> SurfaceFeedback: ...

def validate_feedback(feedback: SurfaceFeedback) -> None:
    if not feedback.request_id: raise ValueError('request_id is required')
    if not feedback.venue_id: raise ValueError('venue_id is required')
    if feedback.observed_at_ms < 0: raise ValueError('observed_at_ms must be non-negative')

def paper_action(action: SurfaceAction) -> SurfaceAction:
    return SurfaceAction(action.request_id, action.venue_id, action.surface, action.action, True)

def feedback_record(feedback: SurfaceFeedback) -> dict[str, Any]:
    validate_feedback(feedback)
    return {
        'request_id': feedback.request_id, 'venue_id': feedback.venue_id,
        'surface': feedback.surface.value, 'state': feedback.state,
        'acknowledged': feedback.acknowledged, 'observed_at_ms': feedback.observed_at_ms,
        'detail': feedback.detail, 'order_reference': feedback.order_reference,
        'paper_only': True, 'execution_authorized': False,
    }