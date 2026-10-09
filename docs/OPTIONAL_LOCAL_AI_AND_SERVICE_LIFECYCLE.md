# Optional Local AI and On-Demand Service Lifecycle

Date: 2026-10-09
Status: architecture decision; automatic lifecycle integration is not yet implemented or production-validated.

## Product boundary

VazaoSovereignTrader is the trading product. Claude Code, FCC/NIM, Ollama, Tailscale, browsers and future local models are optional capabilities, not dependencies of the market/risk/execution loop. The Trader must continue safe local operation when any optional capability is absent, stopped, slow, out of quota or broken.

## Cost policy

- Zero paid inference by default. No cloud-model request may be sent unless a separate explicit setting enables it; the default remains disabled.
- NVIDIA NIM/FCC/Claude Code compatibility aliases are not assumed free just because a service advertises a free tier. Do not invoke them automatically in the Trader.
- The recorded CLI output once displayed `$0.100344`; billing was not confirmed. Treat this as a warning signal and do not spend more quota to investigate automatically.
- No subscription, paid API, billing change or resource purchase is authorized by the Trader.
- The primary future AI provider should be local Ollama or another explicitly installed local runtime, if a suitable model exists and fits available RAM/CPU. Local AI remains optional and may be unavailable on the current weak PC.

## Responsibilities

- Trading core: market data, deterministic strategies, evidence, risk, PAPER execution and recovery. No AI/network call in the hot path.
- Research inbox: accepts the user's question, link or context and creates a durable research request.
- Optional research assistant: may summarize a user-provided public page, explain intent, propose testable hypotheses and draft an interpretation of "what the owner wants". Output is untrusted advisory text, not strategy configuration.
- Evidence pipeline: turns each suggestion into a versioned hypothesis, then measures it against local data, fees, spread, slippage, latency and out-of-sample results. No model may promote itself or change risk gates.
- Claude Code/dashboard: a separate engineering workspace for the owner to request code/document improvements. It must not be a required runtime dependency or an autonomous production-code updater for the Trader.

## On-demand service lifecycle — intended contract

A future `OptionalServiceSupervisor` must be allow-listed and lease-based:

1. Detect health before starting anything.
2. If healthy already, borrow the service and mark it as externally owned; never stop it on release.
3. If unavailable, start only an explicitly allowed local service after an authorized task requests it. Record the exact PID/service instance it started.
4. Poll a local health endpoint with a strict deadline. If startup fails, mark the capability unavailable and return control to the deterministic fallback.
5. Concurrent tasks share one lease/reference count; one task cannot stop a service still used by another.
6. After the final lease is released, wait for a configurable idle grace period. Stop only the instance started by this supervisor, and only if no other lease exists.
7. Never kill processes by broad image-name matching. Never stop a service that was already running before the supervisor acquired it.
8. Start/stop failures, unsupported OS permissions, missing binaries, missing models, OOM, timeouts and service crashes are non-fatal to trading; record sanitized status and continue without AI.
9. Never start Ollama in the market-data/risk hot path. Research jobs are low-priority and may be deferred if the PC is resource constrained.
10. Tailscale is different from an inference daemon: start it only for a requested remote-connectivity task when it is not healthy. Do not stop it while a remote mobile session/lease is active. A cloud endpoint lookup is discovery only; the phone must still connect to and authenticate with the PC directly over Tailscale.

This contract is a design target, not a claim that a supervisor currently exists. Until implemented and tested, services remain manually controlled.

## Automatic PC/mobile discovery

Target flow:

- PC and Android are enrolled to the same authenticated owner account in the Vercel coordination service.
- Both register public device keys; a new phone remains pending until the owner explicitly approves it and proof-of-possession succeeds.
- The PC publishes a short-lived Tailscale-only endpoint lease. The phone obtains that lease through the authenticated service and connects directly to the PC, authenticating again with the paired-device credentials.
- No IP should be typed by the owner during normal reconnects. Manual pairing/bootstrap may still require USB or a one-time approval.
- Vercel must never proxy trading commands, credentials or account state. It provides identity/device approval and endpoint discovery only.
- If Vercel/Internet is down, local PC trading and local research continue. Mobile discovery may be unavailable until service returns; never report the PC as connected until the PC API answers.
- Never accept arbitrary hostnames, public IPs, request-supplied owners or URL destinations as endpoint leases. Validate the exact Tailscale address ranges, owner, device approval, lease expiry and revocation.

## Current observations on PC-Vazao-Anjos (2026-10-09)

- `ollama` CLI exists at `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`, version `0.23.0`.
- `ollama list` could not connect to a running instance; Ollama daemon is currently stopped. Installed model inventory is therefore not yet confirmed.
- `claude` command exists and Node.js/npm are installed. The pinned Node-compatible CLI/FCC setup is documented in `AndreOS-Memory/AndreOS/02_PROJETOS/CLAUDE_CODE_DASHBOARD`.
- `tailscale status` showed PC `100.69.225.47` online and Redmi `100.101.25.85` offline, last seen about 33 minutes earlier. Tailscale was already functional; it must not be stopped as part of this inspection.
- `vercel` CLI was not found in PATH, but the connected Vercel account confirms a Hobby team and a linked `vazao-sovereign-trader` project for this GitHub repository. The latest deployment is `READY` on production and points to commit `7ea1a897` (`Add conversational mobile cockpit`). The project metadata reports `live: false` and SSO protection enabled for deployments except custom domains. This confirms a deployment exists, but does **not** confirm the shared-learning API is publicly reachable or that Supabase is provisioned/configured. Root directory, production endpoint routes and database readiness still need a read-only verification before clients are wired to it.
- QEMU executables were not found in PATH or the first common program-directory check. The phrase "QEMU 2" needs an exact installed-app inventory if it becomes relevant; do not infer that it is installed from this check.
- No optional service was started or stopped during inspection.

## Next implementation order

1. Implement and test the lease-based local service supervisor independently of the trading loop.
2. Add an explicit AI capability interface with provider discovery, cost guard, timeouts, bounded output and deterministic fallback; cloud inference disabled by default.
3. Make research intent understanding optional: local model when available, otherwise preserve the request and ask/produce a conservative structured hypothesis without blocking.
4. Finish Vercel/Supabase endpoint lease API and approved device flow; verify deployment state before connecting clients.
5. Wire PC and Android to authenticated endpoint discovery, direct Tailscale connection, expiry, revocation and offline UX.
6. Only enable automatic lifecycle and cloud discovery after tests prove no trading-loop blocking, no unauthorized service termination, no cross-owner endpoint leakage and correct recovery when services are offline.
