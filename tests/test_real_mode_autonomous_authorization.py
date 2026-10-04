from types import SimpleNamespace

import pytest

from PC_ENGINE.core.engine import SovereignEngine


def test_autonomous_flag_cannot_bypass_fresh_consumed_authorization():
    engine = SimpleNamespace(
        config={"autonomous_execution": {"allow_real": True}},
        real_mode_guard=SimpleNamespace(
            state=SimpleNamespace(last_reason="armed", human_authorized=True)
        ),
        state=SimpleNamespace(status="OFF"),
    )

    with pytest.raises(RuntimeError, match="freshly consumed authorization"):
        SovereignEngine.set_mode(
            engine,
            "REAL",
            real_authorized=True,
            autonomous=True,
        )
