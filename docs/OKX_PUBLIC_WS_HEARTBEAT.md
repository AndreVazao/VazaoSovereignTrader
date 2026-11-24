# OKX public WebSocket application heartbeat

The OKX public L2 collector uses the application-level text heartbeat documented by OKX. This is distinct from WebSocket protocol control-frame ping/pong.

- On an idle connection, after 20 seconds without any inbound message, the collector sends the text frame `ping`.
- It expects the text frame `pong` within 10 seconds.
- If the response does not arrive, it closes the socket. The collector's existing reconnect loop then reconnects and invalidates the previous synchronized book until a fresh snapshot is received.
- If OKX sends a text `ping`, the collector responds with text `pong` without sending it through the market-data JSON parser.
- Heartbeat counters are exposed in the non-sensitive collector health snapshot.

This behavior is public market-data transport maintenance only. It does not authenticate, access account data, submit orders, or change PAPER/LIVE permissions.

The 20-second idle threshold is deliberately below OKX's documented 30-second idle disconnect. The 10-second pong deadline leaves a bounded recovery interval. CI tests validate the heartbeat state machine with a fake socket; live exchange behavior and low-memory Windows endurance still require separate operational validation.

Reference: [OKX API guide — WebSocket connection keepalive](https://www.okx.com/docs-v5/en/).
