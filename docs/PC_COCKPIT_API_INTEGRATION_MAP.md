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

## Virtual Office read-only connection increment

The standalone office shell is served by the same Flask application at `GET /virtual-office`. This avoids a separate-origin browser client for the first integration and lets the operator reach the same backend over LAN or the existing private Tailscale path. The route reads `virtual_office/prototype/full_cockpit_shell.html`, sends `Cache-Control: no-store`, and fails with 404 if the asset is absent.

The shell's connection panel currently:
- requires the operator to enter a token for the page session;
- calls `GET /status` first to verify private-state access, then reads `/venue-health`, `/diagnostics`, `/human-interaction/pending` and `/research`;
- sends the token only in the `X-Token` header, uses GET-only requests with `credentials: omit` and `cache: no-store`, and never stores the token in local storage or a URL;
- has an explicit disconnect action that clears the page's token field and in-memory reference;
- does not expose any mutation or trading command through this connection panel.

**Limitations:** this is the first read-only connection slice, not full cockpit parity. The panel does not yet render detailed typed models for every endpoint, subscribe to a server event stream, reconnect automatically, or integrate the conversational message form with `POST /assistant/message`. The conversation remains a local demo until a separately tested authenticated gateway integration is added. Keep the PC cockpit as the existing capability reference.

Before packaging the office into an EXE or embedding it in Android, verify the HTML asset is included in the distribution. Do not point the UI at a public Vercel URL or turn Vercel into a traffic proxy; open the office from the PC backend's LAN or private Tailscale URL.

### Conversational gateway connection

The office chat form now sends submitted messages to the existing authenticated `POST /assistant/message` gateway, but only after the operator has connected successfully. It uses the same in-memory token and `X-Token` header as the read-only panel; it does not save the token in browser storage or a URL. The server remains the authority for scope checks.

The current gateway is a deterministic command router, not an unconstrained LLM:
- status questions return a snapshot;
- investigation/research requests and URLs are queued only when the principal has `submit_research`;
- PAPER start/pause/resume/stop phrases require `trade_paper` and go through the existing engine methods;
- requests containing REAL/live-money language are explicitly refused and do not arm REAL mode;
- a request without an implemented intent returns a bounded informational response.

The browser displays the gateway's response and execution flags. On a transport error it warns that the outcome is unknown and tells the operator to check state before retrying; it does not automatically replay a mutation. This first pass has no streaming, rich typed rendering, automatic reconnect, or browser end-to-end test yet. Treat the HTML as a prototype until those tests and packaging checks exist.


## Department context in the Virtual Office (2026-10-22)

The office now sends a validated `department` key with `POST /assistant/message` and keeps separate in-memory conversation histories for the selected department for the current browser session. Supported keys: `brain`, `markets`, `radar`, `research`, `paper`, `risk`, `recovery`, `audit`, `human`. Unknown keys are rejected by the gateway; the UI never treats the department name as authorization or execution scope.

This is **context routing, not nine independent agents**. The current `OperatorAssistantGateway` remains a shared deterministic gateway. Status and permitted PAPER controls still target the existing engine boundary. Research requests include the selected department label in the shared research inbox. For other department-specific natural-language requests, the gateway explicitly returns `DEPARTMENT_NOT_CONNECTED` until a real department worker/API is implemented. The office must not imply that a separate chief/agent has answered when none is wired.

The header connection badge now distinguishes the initial demonstration state from authenticated backend connection, refused access and disconnection. Successful authentication clears the static demo messages in the active conversation; the token remains only in page memory. Department conversation history is session-only and is not represented as durable server history.
