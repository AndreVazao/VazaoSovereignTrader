# Existing PC cockpit → Virtual Office integration map

**Source reviewed on 2026-10-20:** `PC_ENGINE/api/cockpit.py`, `PC_ENGINE/api/dashboard.py`, and the route factory `PC_ENGINE/api/server.py` on `main`.

This is a route-level starting inventory, not a claim that every route has been exhaustively reviewed. Keep the existing cockpit as the feature source of truth while the new office is built as another client.

## Existing cockpit capabilities and observed API routes

| UI capability in current `COCKPIT_HTML` | Observed route(s) | Required treatment in the new office |
|---|---|---|
| Overall status, mode, balance/PnL/drawdown, positions, models, preflight, logs | `GET /status` | Read-only first; show unavailable/stale explicitly, never replace missing values with plausible-looking zeros |
| Engine/market-data/storage/recovery diagnostics | `GET /diagnostics`, `GET /market-data-health` | Display source timestamp and stale flag; don't call diagnostics repeatedly without bounded polling |
| Venue health | `GET /venue-health` | Keep operational health separate from profitability/economic evidence |
| Execution-surface catalogue/runtime | `GET /execution-surfaces`, `GET /execution-surfaces/runtime` | Show configured/observed runtime status, not implied ability to execute |
| PAPER venue economics | `GET /venue-economic-evidence` | Enforce the returned PAPER-only, orders-not-submitted and execution-not-authorized invariants |
| PAPER evidence checklist | `GET /evidence-scorecard`, `POST /evidence-scorecard/refresh` | Refresh is a mutation/job trigger; require authorized scope, report progress and server-confirmed result |
| PAPER study / research | `POST /research` and related research routes (verify full route definitions before integration) | Conversation should create a research request, not turn text directly into an order |
| Human intervention | `GET /human-interaction/pending`, `POST /human-interaction/respond`, `POST /human-interaction/cancel` | Render manual authentication/approval prompts; never bypass MFA/CAPTCHA or auto-fill secrets without explicit operator action |
| Device pairing | `POST /mobile-pairing/request`, `GET /mobile-pairing/status/<challenge_id>`, `POST /mobile-pairing/complete`, `GET /mobile-pairing/devices`, `POST /mobile-pairing/revoke` | Owner-token-only operations stay distinct from a paired device's restricted identity; device revocation must take effect server-side |
| Private operator files | `GET /operator-files`, `POST /operator-files/upload`, `GET /operator-files/<folder>/<filename>` | Treat uploads as potentially untrusted; keep file scope and audit visible |
| Evidence ledger | `GET /evidence-ledger`, `GET /evidence-ledger/audit` | Show provenance and audit status, not just scores |
| Diagnostics export | `GET /diagnostics/export` | Use authenticated fetch and a safe download flow; don't leak token in URL |
| Runtime surface instantiate/probe/close | `POST /execution-surfaces/runtime/instantiate`, `POST /execution-surfaces/runtime/probe`, `POST /execution-surfaces/runtime/close` | These require `trade_paper`; clearly label PAPER-only and do not expose as REAL execution controls |

### Critical distinctions

- `GET /health` is deliberately public and returns basic reachability/mode/owner metadata. It is **not** proof of authenticated private-state access.
- `GET /status`, diagnostics, venue health and evidence endpoints require the `read_private_state` scope in the current route factory.
- Execution-surface lifecycle endpoints above require `trade_paper`; don't infer permissions from menu visibility.
- The route factory has explicit `require_token()` / `require_scope()` handling. The new client must use the existing authentication contract and must never put owner tokens in URLs, logs, browser local storage or the office's visual layer.
- Current HTML includes state-changing buttons for start/pause/resume/stop/mode/REAL authorization. Before wiring these into the new shell, inspect each route's exact method, scope, guard, confirmation semantics and tests. No blanket generic command endpoint.
- A transport timeout after a mutation must produce an **outcome unknown / reconcile** state, not automatic POST replay.

## Implementation gates

1. Create route contract tests and a mapping for every visible control: HTTP method, route, payload schema, scope, server guard, response schema, audit event and failure semantics.
2. Implement one shared API client adapter used by both the compact cockpit and office. No duplicated business logic in JavaScript.
3. First integrate read-only `/status`, `/diagnostics`, `/venue-health`, `/evidence-scorecard` and pending-interaction display with timeouts, polling cancellation and freshness metadata.
4. Add contract tests for unauthenticated/insufficient-scope responses, offline/stale data, revoked devices, malformed payloads and server restart.
5. Integrate research conversation and human intervention next; mutation controls remain disabled until each exact route's guard and outcome semantics are verified.
6. Keep all REAL readiness, preflight, risk and human-authorization gates in the engine/server. The UI cannot grant authority.

## Non-goals

No Freqtrade code reuse; no live exchange actions; no new cloud resources; no endpoint exposed publicly; no fake activity; no second engine instance.
