# Private balance discovery is opt-in

VST starts with `capital_venue_discovery.probe_private_balances=false`.
Public market-data collection and PAPER research do not require exchange
credentials and do not need private account endpoints.

With the default setting, the discovery service may report whether both
credential environment variables are present, but it does not instantiate a
private exchange client and does not call `fetch_balance()`.

An operator may explicitly enable read-only balance discovery by setting
`probe_private_balances=true` in the local configuration, or by an explicit
trusted internal call override. This reads account balances only; it does not
place, cancel or transfer orders. Credentials must remain in environment
variables and must never be written to logs, snapshots, shared learning or
repository configuration.

This setting is independent of PAPER/REAL permissions. Enabling balance
visibility does not authorize trading or change risk limits.
