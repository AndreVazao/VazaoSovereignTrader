# PAPER Replay / Execution Engine

Adds a safe PAPER execution layer. It models requested versus effective price, fees, slippage, latency, full/partial fills, rejection, missed opportunities and gross/net P&L. Results are stored under PC_ENGINE/data/paper/.

PAPER never authorizes REAL. The next evolution will replay collected WebSocket events and compare lead/lag execution against a no-signal baseline, including latency and trading costs.
