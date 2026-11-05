from __future__ import annotations

import json

from PC_ENGINE.core.data_vault import MANIFEST_FILENAME, initialize_vault, validate_vault
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def test_learning_records_and_event_history_survive_vault_reinitialization(tmp_path):
    vault = tmp_path / "VazaoSovereignTraderData" / "vault"
    first_init = initialize_vault(vault)
    database = vault / "learning" / "sovereign-learning.sqlite3"

    with SQLiteLearningMemory(database) as memory:
        first = memory.put(
            key="continuity.btc-usdt.binance-bingx",
            value={"net_edge_bps": 1.7, "sample_count": 42},
            department="analysis",
            provenance="paper-replay:continuity-test",
            status="testing",
            confidence=0.61,
        )
        updated = memory.put(
            key=first.key,
            value={"net_edge_bps": 1.9, "sample_count": 57},
            department="analysis",
            provenance="paper-replay:continuity-test-v2",
            status="testing",
            confidence=0.68,
            expected_version=first.version,
        )

    manifest_before = json.loads((vault / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    second_init = initialize_vault(vault)
    manifest_after = json.loads((vault / MANIFEST_FILENAME).read_text(encoding="utf-8"))

    assert first_init["manifest"]["preservation_policy"] == "preserve_on_upgrade_and_uninstall"
    assert manifest_after["created_at_unix"] == manifest_before["created_at_unix"]
    assert second_init["manifest"]["preservation_policy"] == "preserve_on_upgrade_and_uninstall"
    assert validate_vault(vault)["status"] == "healthy"

    with SQLiteLearningMemory(database) as reopened:
        restored = reopened.get("continuity.btc-usdt.binance-bingx")
        assert restored == updated
        assert restored.value == {"net_edge_bps": 1.9, "sample_count": 57}
        assert restored.version == 2
        events = reopened.list_events(key=restored.key)
        assert [(event.version, event.event_type) for event in events] == [
            (1, "put"),
            (2, "put"),
        ]
