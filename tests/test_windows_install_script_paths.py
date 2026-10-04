from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_public_market_data_verifier_uses_valid_source_install_paths():
    script = (REPO_ROOT / "scripts" / "verify_public_market_data.ps1").read_text(
        encoding="utf-8"
    )
    assert 'PC_ENGINE\\.venv\\Scripts\\python.exe' in script
    assert 'PC_ENGINE\\config\\config.local.json' in script
    assert 'PC_ENGINE\\tools\\run_market_data_bootstrap.py' in script
    assert '--config $config --data-dir $dataDir' in script
    assert 'PC_ENGINE.venvScriptspython.exe' not in script
    assert 'PC_ENGINEconfigconfig.local.json' not in script


def test_public_market_data_verifier_fails_closed_on_bad_or_missing_report():
    script = (REPO_ROOT / "scripts" / "verify_public_market_data.ps1").read_text(
        encoding="utf-8"
    )
    assert 'if (-not (Test-Path $report))' in script
    assert 'ConvertFrom-Json' in script
    assert '$result.status -ne "READY"' in script
