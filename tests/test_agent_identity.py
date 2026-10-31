from PC_ENGINE.tools.agent_identity import (
    AgentIdentity,
    AvatarKind,
    OriginType,
    avatar_kind,
    growth_metrics,
)


def identity(agent_id, origin, **kwargs):
    return AgentIdentity(
        agent_id=agent_id,
        origin_type=origin,
        provenance_validated=kwargs.pop("provenance_validated", True),
        **kwargs,
    )


def test_vst_created_agents_use_robot_avatar():
    assert avatar_kind(identity("a1", OriginType.VST_CREATED)) is AvatarKind.ROBOT


def test_human_and_verified_imported_agents_keep_existing_avatar():
    assert avatar_kind(identity("a1", OriginType.HUMAN_CREATED)) is AvatarKind.EXISTING
    assert avatar_kind(identity("a2", OriginType.IMPORTED_VERIFIED)) is AvatarKind.EXISTING


def test_unknown_or_unvalidated_origin_is_neutral_not_guessed():
    assert avatar_kind(identity("a1", OriginType.UNKNOWN)) is AvatarKind.NEUTRAL
    assert avatar_kind(
        identity("a2", OriginType.VST_CREATED, provenance_validated=False)
    ) is AvatarKind.NEUTRAL


def test_growth_metrics_exclude_unpersisted_unvalidated_and_placeholders():
    rows = [
        identity("real", OriginType.VST_CREATED, active=True),
        identity("real", OriginType.VST_CREATED, active=True),  # duplicate restore
        identity("quarantined", OriginType.HUMAN_CREATED, active=True, quarantined=True),
        identity("unvalidated", OriginType.VST_CREATED, provenance_validated=False),
        identity("not-persisted", OriginType.VST_CREATED, persisted=False),
        identity("demo", OriginType.VST_CREATED, placeholder=True),
        identity("inactive", OriginType.HUMAN_CREATED, active=False),
    ]
    metrics = growth_metrics(rows)
    assert metrics == {
        "validated_total": 3,
        "active": 1,
        "quarantined": 1,
        "inactive": 1,
        "placeholders_excluded": 1,
    }


def test_growth_metrics_accept_generator_input():
    rows = (identity(f"a{i}", OriginType.VST_CREATED, placeholder=(i == 1)) for i in range(3))
    assert growth_metrics(rows)["placeholders_excluded"] == 1
