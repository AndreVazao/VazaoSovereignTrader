from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_packaged_installer_documentation_matches_manual_first_installer() -> None:
    installer = (ROOT / "installer" / "VazaoSovereignTrader.iss").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "WINDOWS_ONE_CLICK_INSTALL.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "[Run]" not in installer
    assert "/Create" not in installer
    assert "does not start the engine" in guide
    assert "does not register Windows scheduled tasks" in guide
    assert "não inicia automaticamente" in readme.lower()


def test_first_install_guides_do_not_request_exchange_trading_credentials() -> None:
    paths = (
        "README.md",
        "docs/QUICKSTART_WINDOWS.md",
        "docs/PC_PRODUCTION_CHECKLIST.md",
        "docs/PC_INSTALL_AND_DATA_COLLECTION.md",
    )
    for path in paths:
        content = (ROOT / path).read_text(encoding="utf-8").lower()
        assert "spot trading: ligado" not in content
        assert "spot trade apenas" not in content

    checklist = (ROOT / "docs" / "PC_PRODUCTION_CHECKLIST.md").read_text(encoding="utf-8")
    assert "não configurar api keys privadas de exchanges" in checklist.lower()


def test_windows_secrets_helper_only_configures_local_api_token() -> None:
    script = (ROOT / "scripts" / "configure_windows_secrets.ps1").read_text(encoding="utf-8")

    assert "VST_LOCAL_TOKEN" in script
    assert "-AsSecureString" in script
    assert "BINANCE_KEY" not in script
    assert "BINANCE_PRIVATE" not in script
    assert "API credentials" in script



def test_security_and_remote_guides_match_current_paper_only_scope() -> None:
    security = (ROOT / "docs" / "SECURITY.md").read_text(encoding="utf-8").lower()
    remote = (ROOT / "docs" / "REMOTE_MOBILE_SETUP.md").read_text(encoding="utf-8").lower()
    assert "não configurar api keys privadas" in security
    assert security.count("setx binance_key") == 1
    assert "não usar exemplos" in security
    assert "spot trading" not in security
    assert "paper-only" in remote
    assert "ainda não estão certificados de ponta a ponta" in remote
    assert "port-forward da porta 8765" in remote


def test_setup_helpers_never_prompt_for_exchange_credentials() -> None:
    secret_helper = (ROOT / "scripts" / "configure_windows_secrets.ps1").read_text(encoding="utf-8")
    token_helper = (ROOT / "scripts" / "ensure_windows_token.ps1").read_text(encoding="utf-8")
    assert "BINANCE_KEY" not in secret_helper
    assert "BINANCE_PRIVATE" not in secret_helper
    assert "BINGX_KEY" not in secret_helper
    assert "VST_LOCAL_TOKEN" in secret_helper
    assert "VST_LOCAL_TOKEN" in token_helper


def test_setup_messages_make_autostart_explicitly_optional() -> None:
    setup = (ROOT / "scripts" / "setup_windows.ps1").read_text(encoding="utf-8").lower()
    batch = (ROOT / "scripts" / "windows_setup.bat").read_text(encoding="utf-8").lower()
    verifier = (ROOT / "scripts" / "verify_public_market_data.ps1").read_text(encoding="utf-8").lower()
    assert "optional source-checkout autostart only after local validation" in setup
    assert "opcional, apenas apos validacao local" in batch
    assert "autostart is optional" in verifier



def test_source_setup_keeps_callers_working_directory_and_checks_native_exit_codes() -> None:
    setup = (ROOT / "scripts" / "setup_windows.ps1").read_text(encoding="utf-8")
    assert "Set-Location $pc" not in setup
    assert setup.count("$LASTEXITCODE -ne 0") >= 3
    assert "Python virtual environment was not created" in setup


def test_manual_token_override_requires_a_long_local_api_token() -> None:
    script = (ROOT / "scripts" / "configure_windows_secrets.ps1").read_text(encoding="utf-8")
    assert "$token.Length -lt 32" in script
