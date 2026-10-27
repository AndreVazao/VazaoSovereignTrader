# Runtime API bind hardening — 2026-10-27

## Finding

The server entrypoint fell back to `0.0.0.0` when the configured host was absent, and the example configuration also specified `0.0.0.0`. That binds the HTTP API on every IPv4 interface and conflicts with the documented local-first/private-network boundary. Token authentication is still required by routes, but authentication does not justify unnecessary network exposure.

## Change on the active consolidation branch

- The entrypoint now defaults to `127.0.0.1`.
- Empty host values and wildcard addresses (`0.0.0.0`, `::`, `[::]`) are forced back to loopback.
- The example configuration now uses loopback.
- A specific non-wildcard address can still be configured deliberately for a trusted LAN/Tailscale interface. It must remain protected by token/device authentication and firewall/private-network controls.
- Added regression tests for missing/blank host, wildcard rejection and preservation of an explicit specific address.

## Migration note

Existing `config.local.json` files are not rewritten automatically. On an installation that already has a local configuration, inspect `server.host` before starting the runtime. Replace wildcard values with `127.0.0.1` for local-only operation or with a specific private LAN/Tailscale address when remote clients have been configured and approved. Do not expose the API directly to the public Internet.

## Verification status

The change is committed to the existing PR branch. Current-head Python CI must pass before merge. This is a configuration-boundary hardening change, not proof that the complete remote pairing or Tailscale flow has been tested end to end.
