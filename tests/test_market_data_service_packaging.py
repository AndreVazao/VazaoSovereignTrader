from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_build_packages_every_supervised_worker():
    script = (ROOT / "scripts" / "build_windows_installer.ps1").read_text(encoding="utf-8")
    installer = (ROOT / "installer" / "VazaoSovereignTrader.iss").read_text(encoding="utf-8")
    required = (
        "VazaoSovereignTrader-MarketData",
        "VazaoSovereignTrader-Radar",
        "VazaoSovereignTrader-TopOfBook",
        "VazaoSovereignTrader-L2",
        "VazaoSovereignTrader-MarketDataService",
    )
    for binary in required:
        assert binary in script
        assert f"build\\{binary}.exe" in installer


def test_windows_installer_exposes_graceful_start_and_stop():
    installer = (ROOT / "installer" / "VazaoSovereignTrader.iss").read_text(encoding="utf-8")
    build = (ROOT / "scripts" / "build_windows_installer.ps1").read_text(encoding="utf-8")
    assert "Iniciar recolha contínua" in installer
    assert "Parar recolha contínua" in installer
    assert "stop_market_data_service.ps1" in installer
    assert "stop_market_data_service.ps1" in build
    assert "PUBLIC_MARKET_DATA_SERVICE.md" in build
    assert "PUBLIC_MARKET_DATA_SERVICE.md" in installer
    assert "function InitializeUninstall(): Boolean;" in installer
    assert "ResultCode <> 0" in installer
    assert "ewWaitUntilTerminated" in installer


def test_windows_uninstall_aborts_when_market_data_shutdown_is_not_confirmed():
    installer = (ROOT / "installer" / "VazaoSovereignTrader.iss").read_text(encoding="utf-8")
    uninstall_run = installer.split("[UninstallRun]", 1)[1].split("[Code]", 1)[0]
    code = installer.split("[Code]", 1)[1]

    assert "stop_market_data_service.ps1" not in uninstall_run
    assert "function InitializeUninstall(): Boolean;" in code
    assert "Exec(PowerShellExe" in code
    assert "ewWaitUntilTerminated" in code
    assert "ResultCode <> 0" in code
    assert "Result := False" in code
