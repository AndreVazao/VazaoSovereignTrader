from __future__ import annotations

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
    print("Default mode is PAPER. Use the API or mobile cockpit to start.")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
