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
