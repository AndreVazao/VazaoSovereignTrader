from PC_ENGINE.core.connectivity_policy import (
    ConnectivityEvidence,
    ConnectivityMode,
    evaluate_connectivity,
)


def evidence(**overrides):
    values = {
        "lan_peers_authenticated": True,
        "overlay_peers_authenticated": False,
        "required_peers_reachable": True,
        "reconciliation_required": False,
        "state_consistent": True,
        "vercel_available": False,
    }
    values.update(overrides)
    return ConnectivityEvidence(**values)


def test_authenticated_lan_is_preferred_without_vercel():
    assert evaluate_connectivity(evidence()) is ConnectivityMode.CONNECTED_LAN


def test_authenticated_private_overlay_is_fallback():
    assert evaluate_connectivity(
        evidence(lan_peers_authenticated=False, overlay_peers_authenticated=True)
    ) is ConnectivityMode.CONNECTED_PRIVATE_OVERLAY


def test_missing_required_peers_forces_research_only_even_if_vercel_is_up():
    assert evaluate_connectivity(
        evidence(
            lan_peers_authenticated=False,
            overlay_peers_authenticated=False,
            required_peers_reachable=False,
            vercel_available=True,
        )
    ) is ConnectivityMode.PARTITIONED_RESEARCH_ONLY


def test_vercel_outage_does_not_block_authenticated_lan():
    assert evaluate_connectivity(evidence(vercel_available=False)) is ConnectivityMode.CONNECTED_LAN


def test_rejoin_requires_reconciliation_before_normal_mode():
    assert evaluate_connectivity(
        evidence(reconciliation_required=True)
    ) is ConnectivityMode.RECONCILING


def test_reconciliation_with_unreachable_peers_stays_research_only():
    assert evaluate_connectivity(
        evidence(reconciliation_required=True, required_peers_reachable=False)
    ) is ConnectivityMode.PARTITIONED_RESEARCH_ONLY


def test_inconsistent_state_is_degraded_not_normal():
    assert evaluate_connectivity(
        evidence(state_consistent=False)
    ) is ConnectivityMode.CONNECTED_DEGRADED


def test_inconsistent_state_during_reconciliation_is_degraded():
    assert evaluate_connectivity(
        evidence(reconciliation_required=True, state_consistent=False)
    ) is ConnectivityMode.CONNECTED_DEGRADED


def test_no_authenticated_path_fails_closed():
    assert evaluate_connectivity(
        evidence(
            lan_peers_authenticated=False,
            overlay_peers_authenticated=False,
        )
    ) is ConnectivityMode.PARTITIONED_RESEARCH_ONLY
