from pathlib import Path


def test_windows_installer_never_creates_unattended_tasks_or_closes_apps():
    installer = Path("installer/VazaoSovereignTrader.iss").read_text(encoding="utf-8")

    assert "CloseApplications=no" in installer
    assert "[Run]" not in installer
    assert "/Create" not in installer
    assert "VazaoSovereignTrader-MarketData.exe" in installer
    assert "[UninstallRun]" in installer


def test_windows_uninstall_does_not_delete_browser_profiles_or_user_vault():
    installer = Path("installer/VazaoSovereignTrader.iss").read_text(encoding="utf-8")

    assert "[UninstallDelete]" not in installer
    assert "VazaoSovereignTraderData" not in installer
    assert 'Type: filesandordirs; Name: "{app}\\data\\browser\\profiles"' not in installer
