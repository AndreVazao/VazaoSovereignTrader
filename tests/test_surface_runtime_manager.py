from __future__ import annotations

from PC_ENGINE.execution.surface_adapters import Surface
from PC_ENGINE.execution.surface_runtime_manager import ExecutionSurfaceRuntimeManager


def _config(tmp_path):
    return {
        'browser': {
            'profile_dir': str(tmp_path / 'profiles'), 'headless': True, 'timeout_ms': 1000,
            'platforms': {'browser-demo': {'surface': 'WEB_BROWSER', 'url': 'https://example.invalid'}},
        },
        'execution_surface': {
            'feedback_path': str(tmp_path / 'feedback.jsonl'),
            'platforms': {
                'desktop-demo': {'surface': 'DESKTOP_APP', 'executable_path': str(tmp_path / 'demo.exe')},
                'android-demo': {'surface': 'ANDROID_APK', 'package_name': 'com.example.demo'},
            },
        },
    }


def test_manager_construction_is_inert(tmp_path):
    manager = ExecutionSurfaceRuntimeManager(_config(tmp_path))
    snapshot = manager.snapshot()
    assert snapshot['adapters'] == []
    assert snapshot['orders_submitted'] is False
    assert snapshot['execution_authorized'] is False


def test_manager_instantiates_without_probing_or_starting_transport(tmp_path):
    manager = ExecutionSurfaceRuntimeManager(_config(tmp_path))
    record = manager.instantiate(runtime_id='browser-1', venue_id='browser-demo', surface=Surface.WEB_BROWSER)
    assert record['state'] == 'INSTANTIATED'
    assert manager.snapshot()['adapters'][0]['runtime_id'] == 'browser-1'
    assert manager.runtime.get('browser-1') is not None
    assert not (tmp_path / 'feedback.jsonl').exists()


def test_manager_builds_desktop_and_android_configs_without_starting_them(tmp_path):
    manager = ExecutionSurfaceRuntimeManager(_config(tmp_path))
    desktop = manager.build_adapter_config(venue_id='desktop-demo', surface=Surface.DESKTOP_APP)
    android = manager.build_adapter_config(venue_id='android-demo', surface=Surface.ANDROID_APK)
    assert desktop.executable_path.endswith('demo.exe')
    assert android.package_name == 'com.example.demo'


def test_manager_requires_explicit_configured_venue(tmp_path):
    manager = ExecutionSurfaceRuntimeManager(_config(tmp_path))
    try:
        manager.instantiate(runtime_id='missing', venue_id='unknown', surface=Surface.WEB_BROWSER)
    except ValueError as exc:
        assert 'surface configuration not found' in str(exc)
    else:
        raise AssertionError('missing venue configuration must fail closed')



def test_manager_rejects_requested_surface_mismatch(tmp_path):
    manager = ExecutionSurfaceRuntimeManager(_config(tmp_path))
    try:
        manager.build_adapter_config(venue_id='browser-demo', surface=Surface.DESKTOP_APP)
    except ValueError as exc:
        assert 'surface mismatch' in str(exc)
    else:
        raise AssertionError('configured surface mismatch must fail closed')


def test_manager_exposes_configured_runtime_health_window(tmp_path):
    config = _config(tmp_path)
    config["execution_surface"]["runtime_health_stale_after_ms"] = 12_345
    manager = ExecutionSurfaceRuntimeManager(config)
    assert manager.runtime_health_stale_after_ms() == 12_345
    assert manager.snapshot()["health_policy"]["stale_after_ms"] == 12_345


def test_manager_rejects_negative_runtime_health_window(tmp_path):
    config = _config(tmp_path)
    config["execution_surface"]["runtime_health_stale_after_ms"] = -1
    manager = ExecutionSurfaceRuntimeManager(config)
    try:
        manager.snapshot()
    except ValueError as exc:
        assert "must be >= 0" in str(exc)
    else:
        raise AssertionError("negative runtime health window must fail closed")
