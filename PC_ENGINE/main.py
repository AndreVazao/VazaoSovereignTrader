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


def main() -> None:
    config = load_config()
    engine = SovereignEngine(config)
    app = create_app(engine, config.get("server", {}).get("local_control_token_env", "VST_LOCAL_TOKEN"))
    host = config.get("server", {}).get("host", "0.0.0.0")
    port = int(config.get("server", {}).get("port", 8765))
    print(f"VazaoSovereignTrader PC_ENGINE online at http://{host}:{port}")
    print("Default mode is PAPER. Use the API, dashboard, or mobile cockpit to start.")
    print(f"Local dashboard: http://127.0.0.1:{port}/dashboard")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
