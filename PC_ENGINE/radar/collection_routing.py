from __future__ import annotations

from collections.abc import Iterable

from PC_ENGINE.radar.venue_discovery import VenueDiscoveryRegistry


def reviewed_stream_venues(
    registry: VenueDiscoveryRegistry,
    supported_by_collector: Iterable[str],
    requested: Iterable[str] | None = None,
) -> list[str]:
    """Resolve venue names without promoting unverified or unsupported streams."""
    collector_support = {name.lower() for name in supported_by_collector}
    reviewed = {
        venue.venue_id
        for venue in registry.list_venues()
        if venue.lifecycle == "public_research_only"
        and venue.public_websocket != "not_verified"
        and venue.venue_id in collector_support
    }
    if requested is None:
        return sorted(reviewed)
    selected = list(dict.fromkeys(name.lower() for name in requested))
    rejected = sorted(set(selected) - reviewed)
    if rejected:
        raise ValueError("venues_not_reviewed_for_public_streams:" + ",".join(rejected))
    return selected
