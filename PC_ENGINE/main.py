from __future__ import annotations

import sys
from pathlib import Path

# Allows running both from repo root (`python PC_ENGINE/main.py`) and from PC_ENGINE (`python main.py`).
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PC_ENGINE.api.server import create_app
from PC_ENGINE.core.config import load_config
from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.paper_confluence_engine import PaperConfluenceEngine


def _should_auto_start_paper(config: dict, mode: str) -> bool:
    """Allow unattended PAPER startup, never unattended REAL startup."""
    return str(mode).upper() == "PAPER" and bool(
        config.get("engine", {}).get("auto_start_paper", True)
    )


def main() -> None:
    config = load_config()
    mode = str(config.get("mode", "PAPER")).upper()
    confluence_enabled = bool(config.get("confluence", {}).get("enabled", True))
    if mode == "PAPER" and confluence_enabled:
        engine = PaperConfluenceEngine(config)
        print("PAPER Confluence gate: ENABLED")
    else:
        engine = SovereignEngine(config)
        print("PAPER Confluence gate: DISABLED")
    app = create_app(engine, config.get("server", {}).get("local_control_token_env", "VST_LOCAL_TOKEN"))
    host = config.get("server", {}).get("host", "0.0.0.0")
    port = int(config.get("server", {}).get("port", 8765))
    if _should_auto_start_paper(config, mode):
        engine.start()
        print("PAPER engine auto-start: ENABLED")
    else:
        print("PAPER engine auto-start: DISABLED")
    print(f"VazaoSovereignTrader PC_ENGINE online at http://{host}:{port}")
    print("Default mode is PAPER. Use the API, dashboard, or mobile cockpit to control the engine.")
    print(f"Local dashboard: http://127.0.0.1:{port}/dashboard")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
