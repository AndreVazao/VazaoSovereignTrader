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
- `ollama list` could not connect to a running instance; Ollama daemon is currently stopped. Read-only inspection of the model cache (without starting the daemon) found four installed manifests: `deepseek-r1:1.5b`, `llama3.2:1b`, `qwen2.5:1.5b`, and `qwen2.5-coder:1.5b`; the blob cache was about 4.11 GB. Model runtime readiness has not yet been tested.
- `claude` command exists and Node.js/npm are installed. The pinned Node-compatible CLI/FCC setup is documented in `AndreOS-Memory/AndreOS/02_PROJETOS/CLAUDE_CODE_DASHBOARD`.
- `tailscale status` showed PC `100.69.225.47` online and Redmi `100.101.25.85` offline, last seen about 33 minutes earlier. Tailscale was already functional; it must not be stopped as part of this inspection.
- `vercel` CLI was not found in PATH, but the connected Vercel account confirms the `vazao-sovereign-trader` project and a `READY` production deployment at commit `7ea1a897` (`Add conversational mobile cockpit`). Read-only HTTP checks against `https://vazao-sovereign-trader.vercel.app/api/health` returned `200` with `service=vazao-shared-learning`; GET `/api/v1/devices/endpoint` returned `405`, matching the route's signed-POST-only contract. Thus the API routes are deployed and reachable on this alias. Project metadata still reports `live: false` and SSO protection for non-custom domains, so the other aliases should not be assumed public.
- Read-only Vercel environment inventory returned **zero configured environment variables** (`hiddenProductionEnvCount: 0`). The connected Supabase account lists only `baribudos-studio-website`, which is `INACTIVE`; no separate Trader/shared-learning Supabase project was found. Therefore database-backed auth/device endpoint actions are **not production-ready** and likely return `service_not_configured`/503 once a valid token reaches the handler. No credentials were read, no project was created, and no deployment/environment setting was changed. Provisioning any database requires a separate cost/organization decision and is not authorized by the zero-spend policy.
- QEMU executables were not found in PATH or the first common program-directory check. The phrase "QEMU 2" needs an exact installed-app inventory if it becomes relevant; do not infer that it is installed from this check.
- No optional service was started or stopped during inspection.

## Next implementation order

1. **Done locally:** implement/test the lease-based Ollama supervisor independently of the trading loop. Six supervisor tests pass; a real-model smoke test remains pending.
2. **Done locally:** add the local-only AI interface with cached-model detection, bounded I/O, short inference keep-alive, no download and deterministic fallback. Cloud inference is not implemented.
3. **Done locally:** let successful public-link research optionally use the local model for owner-intent interpretation; model output is advisory only. A focused integration test and a real local inference smoke test remain pending.
4. **Blocked by infrastructure/cost policy:** endpoint-lease routes exist in Vercel source and are deployed, but Vercel currently has zero environment variables and no active Trader/shared-learning Supabase project was found. Do not create/provision a database without first confirming the actual plan and zero-cost implications.
5. Wire PC and Android to authenticated endpoint discovery, direct Tailscale connection, expiry, revocation and offline UX after backend readiness is proven.
6. Implement Tailscale lifecycle with session leases only after mobile discovery works; never stop an already-running Tailscale service or one with an active mobile session.
7. Only enable automatic lifecycle and cloud discovery after tests prove no trading-loop blocking, no unauthorized service termination, no cross-owner endpoint leakage and correct recovery when services are offline.


## Implementation checkpoint (2026-10-09)

Implemented locally, not yet merged to `main`:

- `PC_ENGINE/services/optional_service_supervisor.py`: allow-listed Ollama lifecycle, local health check, process ownership, shared leases, idle grace, exact-process termination and bounded startup. It never manages Tailscale yet; Tailscale is deliberately left alone because it is already the active remote path.
- `PC_ENGINE/research/local_context_assistant.py`: local-only Ollama provider, cached-model detection without daemon startup, 8,000-character input bounds, 64 KiB response bound, 30-second maximum request timeout, `keep_alive=0`, no model download, and `VST_LOCAL_CONTEXT_AI=off` override. Cloud inference is not implemented.
- `PC_ENGINE/research/worker.py`: after a public page is successfully retrieved, optionally asks the local model to interpret owner intent and summarize testable hypotheses. The output is appended as explicitly unvalidated advisory text only; it cannot alter the deterministic category, evaluation result, risk or execution.
- No daemon is started merely by constructing the worker. It is acquired only for a successfully fetched public research page. When done, the model is unloaded and the owned Ollama process is eligible to stop after the idle grace period. A pre-existing Ollama instance is borrowed and never stopped by this supervisor.
- Focused tests cover external-service reuse, shared leases, timeout cleanup, allow-list, idempotent release, bounded advisory output and fail-open behavior. Runtime validation against the real installed models has not yet been performed; do not claim those models work until a user-authorized local smoke test is run.

Still outstanding: Tailscale service start/stop leases (must not interrupt mobile access), end-to-end verification of the Vercel endpoint lease API and Android discovery, and integration testing of local inference under the PC's memory/CPU constraints.


### Verification follow-up (2026-10-09)

- After wiring the local context assistant into the research worker, focused tests were rerun with `VST_LOCAL_CONTEXT_AI=off` to guarantee the tests themselves would not start the installed Ollama daemon: **17 passed** across supervisor/context/research tests, then **8 passed** across REAL-order boundary tests. Python compilation and `git diff --check` passed. Combined: **25 passed**. This validates deterministic fallback and contracts, not actual local model quality.
- Read-only live API checks: health endpoint `200`; endpoint-lease route GET `405`; unauthenticated endpoint-lease POST `{}` returns `401 unauthorized` as required. No authenticated/device write was attempted.
- Vercel environment inventory has zero configured variables; Supabase inventory contains only the unrelated inactive website project. API routing is deployed, but authenticated device discovery is blocked until a correctly scoped Supabase backend and environment are provisioned. No resources, paid services, credentials, or deployment settings were changed.
