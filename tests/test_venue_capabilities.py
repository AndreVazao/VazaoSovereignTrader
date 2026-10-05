from PC_ENGINE.core.venue_capabilities import VenueCapability, VenueCapabilityRegistry, build_real_execution_requirements


def test_declared_capability_is_not_executable_until_verified():
    registry = VenueCapabilityRegistry({
        "TEST": {
            "real_order_submit": {
                "declared": True,
                "verified": False,
                "environment": "REAL",
            }
        }
    })
    ok, blockers = registry.verify_required(["TEST"], ["real_order_submit"], "REAL")
    assert not ok
    assert blockers == ["TEST:real_order_submit:not_verified"]


def test_verified_capability_requires_matching_environment():
    registry = VenueCapabilityRegistry()
    registry.register(VenueCapability(
        venue="TEST",
        capability="real_order_submit",
        declared=True,
        verified=True,
        environment="PAPER",
    ))
    ok, blockers = registry.verify_required(["TEST"], ["real_order_submit"], "REAL")
    assert not ok
    assert blockers == ["TEST:real_order_submit:missing"]


def test_real_requirements_are_explicit_and_serializable():
    requirements = build_real_execution_requirements()
    assert "real_order_submit" in requirements
    assert "real_order_cancel" in requirements
    assert "market_data_realtime" in requirements
