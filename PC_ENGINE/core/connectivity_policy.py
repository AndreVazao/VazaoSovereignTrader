"""Fail-closed connectivity policy for the Sovereign Trader supervisor.

Pure policy only: this module performs no network I/O, elects no leader, and
cannot grant execution authority. A supervisor must authenticate peer probes
and enforce the returned mode at operation boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConnectivityMode(str, Enum):
    CONNECTED_LAN = "connected_lan"
    CONNECTED_PRIVATE_OVERLAY = "connected_private_overlay"
    PARTITIONED_RESEARCH_ONLY = "partitioned_research_only"
    RECONCILING = "reconciling"
    CONNECTED_DEGRADED = "connected_degraded"


@dataclass(frozen=True)
class ConnectivityEvidence:
    """Authenticated, recent observations supplied by the supervisor.

    `required_peers_reachable` means all peers required for this host's role
    have authenticated successfully, not merely that an IP answered a ping.
    `reconciliation_required` must be set after a partition/rejoin or whenever
    peer cursors, leadership epoch, checkpoints, or task journals may differ.
    """
    lan_peers_authenticated: bool
    overlay_peers_authenticated: bool
    required_peers_reachable: bool
    reconciliation_required: bool = False
    state_consistent: bool = True
    vercel_available: bool = False


def evaluate_connectivity(evidence: ConnectivityEvidence) -> ConnectivityMode:
    """Resolve safe operating mode; never promotes a leader or grants authority.

    The LAN is preferred. An authenticated private overlay is an acceptable
    fallback. Vercel availability alone cannot replace missing peer connectivity
    and is not proof of a current leadership grant.
    """
    if evidence.reconciliation_required:
        if not evidence.required_peers_reachable:
            return ConnectivityMode.PARTITIONED_RESEARCH_ONLY
        if not evidence.state_consistent:
            return ConnectivityMode.CONNECTED_DEGRADED
        return ConnectivityMode.RECONCILING

    if not evidence.required_peers_reachable:
        return ConnectivityMode.PARTITIONED_RESEARCH_ONLY

    if not evidence.state_consistent:
        return ConnectivityMode.CONNECTED_DEGRADED

    if evidence.lan_peers_authenticated:
        return ConnectivityMode.CONNECTED_LAN

    if evidence.overlay_peers_authenticated:
        return ConnectivityMode.CONNECTED_PRIVATE_OVERLAY

    return ConnectivityMode.PARTITIONED_RESEARCH_ONLY
