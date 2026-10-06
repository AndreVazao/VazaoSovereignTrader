from __future__ import annotations

from PC_ENGINE.core.recovery import RecoveryManager


def test_save_positions_uses_durable_atomic_writer_for_primary_and_backup(tmp_path, monkeypatch):
    manager = RecoveryManager(state_path=tmp_path / "runtime_state.json")
    calls = []

    original = manager._write_json_atomic

    def tracked(path, payload):
        calls.append(path)
        return original(path, payload)

    monkeypatch.setattr(manager, "_write_json_atomic", tracked)

    manager.save_positions({})

    assert calls == [manager.state_path, manager.backup_path]
    assert manager.state_path.exists()
    assert manager.backup_path.exists()
    assert manager.load_state()["recovery_source"] == "primary"


def test_clear_reconciliation_fsyncs_directory_after_unlink(tmp_path, monkeypatch):
    manager = RecoveryManager(state_path=tmp_path / "runtime_state.json")
    manager.prepare_reconciliation({"positions": {}})

    calls = []
    monkeypatch.setattr(
        manager,
        "_fsync_directory",
        lambda path: calls.append(path),
    )

    manager.clear_reconciliation()

    assert calls == [manager.reconciliation_journal_path.parent]
    assert not manager.reconciliation_journal_path.exists()


def test_atomic_writer_fsyncs_directory_after_replace(tmp_path, monkeypatch):
    manager = RecoveryManager(state_path=tmp_path / "runtime_state.json")
    calls = []
    monkeypatch.setattr(manager, "_fsync_directory", lambda path: calls.append(path))

    manager._write_json_atomic(manager.state_path, {"ok": True})

    assert calls == [manager.state_path.parent]
    assert manager.state_path.read_text(encoding="utf-8").strip() == '{"ok": true}'
