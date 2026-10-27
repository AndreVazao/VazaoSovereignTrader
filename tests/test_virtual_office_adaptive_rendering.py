from pathlib import Path


def test_adaptive_rendering_profiles_are_present():
    path = Path(__file__).resolve().parents[1] / "virtual_office" / "prototype" / "index.html"
    html = path.read_text(encoding="utf-8")
    assert 'value="auto"' in html
    assert 'value="pixel"' in html
    assert 'value="stick"' in html
    assert 'value="compact"' in html
    assert 'value="hd" disabled' in html
    assert 'navigator.deviceMemory' in html
    assert 'navigator.hardwareConcurrency' in html
    assert 'if(slowWindows>=2)degrade(' in html
