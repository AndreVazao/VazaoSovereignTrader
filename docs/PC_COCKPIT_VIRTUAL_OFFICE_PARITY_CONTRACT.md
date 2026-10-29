# PC Cockpit + Virtual Office — functional parity contract

**Branch:** `feat/pc-cockpit-full-office-shell-2026-10-20`
**Status:** first responsive interaction shell; demo-only, not connected to the trading engine.

## Product decision
The Virtual Office is a complete alternative interface to the PC cockpit, not a decorative map. It must expose the same permitted capabilities and server-authoritative state. The office adds visual navigation; it must not remove functions available in the compact/conversational cockpit.

## Three persistent regions
- **Left navigation:** overview, office, conversational cockpit, markets/exchanges, research, strategies/PAPER, risk/readiness, events/audit, devices and settings.
- **Central workspace:** responsive 2D/2.5D rooms for CEO/brain, exchange integrations, Market Radar, Exchange Comparison, Investigation, Analysis, Central Learning Memory, Fast Response, PAPER lab, risk, recovery, audit and human intervention. Market Radar and Exchange Comparison remain distinct; Investigation and Analysis remain distinct. Central Memory is one visual room over the shared local memory service, not a second store.
- **Right conversation panel:** persistent chat, requests and alerts. Natural-language requests are sent only to the authenticated backend once integration is implemented.

On mobile/narrow windows, the sidebars collapse to overlays and the center switches to a compact or chat-first layout. Keep keyboard focus, visible labels, reduced-motion support and accessible control names.

## Authority and security
- The headless PC/server backend remains the only authority for market data, trading state, balances, positions, orders, risk, readiness and audit.
- Cockpit and office are clients of the same API. They may not instantiate a second engine or keep independent authoritative state.
- Display live status only when sourced from a successful API response/event with freshness metadata. Empty, stale, disconnected and unauthorized are distinct states.
- Every privileged command is authenticated, scoped to the paired device, checked against server-side risk/readiness gates and audited. UI visibility is not authorization.
- Do not claim command success before server confirmation. For timeout/connection loss after a mutation, display outcome unknown and reconcile; never automatically replay non-idempotent commands.
- Exchange secrets stay on the backend. Client configuration may store endpoint metadata and protected device credentials only.
- Home route: configured LAN endpoint. Away-from-home route: configured Tailscale endpoint. LAN operation must not depend on Vercel or Tailscale. Vercel is discovery/enrollment coordination, never an order relay or permanent traffic proxy. No public unauthenticated fallback.
- Human login/2FA/CAPTCHA challenges remain manual and can be presented as pending-intervention requests; never bypass them.
- Office movement, agents, carriers, transfers and metrics are illustrative until bound to real, timestamped backend events. The UI must label demo state.

## First shell delivered in this increment
`virtual_office/prototype/full_cockpit_shell.html` is a standalone, dependency-free responsive interaction prototype:
- left-side navigation, central department map and persistent right-side conversation panel;
- separate selectable rooms and conversation labels for Exchange Comparison, Analysis, Central Memory and Fast Response, alongside the previously listed departments;
- responsive room grid that shifts from four columns to three and then two on narrower screens;
- office, compact and conversation presentation modes;
- selectable departments and chat/requests/alerts tabs;
- narrow-screen sidebar overlays;
- demo labels that make clear no backend request or trading action occurs.

This is a visual/interaction shell only. The chat is intentionally local demo behavior. It does not claim API integration, authenticated commands, live events, installation packaging or production readiness.

## Integration sequence
1. Inventory the current PC cockpit and API routes; map every existing capability to a named API action and response schema.
2. Add a typed client adapter with explicit connection/authentication states, timeouts, cancellation and freshness tracking.
3. Integrate read-only health/status/events first, including stale/offline behavior and contract tests.
4. Integrate conversational requests and human-intervention workflows, with server-confirmed outcomes and audit references.
5. Integrate permitted controls only after checking server-side auth, scopes, idempotency, readiness and risk gates.
6. Validate LAN at home, Tailscale away, Vercel outage, backend restart, revoked device, stale responses, ambiguous mutation timeout, small screens and keyboard accessibility.
7. Only after these gates, bind office room/agent animations to real backend events. Preserve compact/chat fallback and keep 3D optional.

## Acceptance criteria
- Office and compact cockpit provide equivalent permitted actions and status.
- Both use one backend and show consistent server-authoritative data.
- Conversation panel remains available from every department.
- No fabricated live activity, no client-held exchange keys, no unauthorized/public fallback.
- Disconnects, stale data, permission failures and unknown mutation outcomes are explicit.
- Chat-only mode remains usable on low-power devices.


## Verified work, local social animation and department focus

- Ambient movement (walk, café, corridor, gym, exterior) runs locally on the client and is explicitly labelled as visual/social simulation. It does not require a backend connection and never proves that an agent is working.
- A task progress bar is rendered only after the client receives a backend-authenticated task snapshot containing `backendConfirmed: true`, department, task ID, agent ID, status and a valid progress value. A completed task is shown at 100% only when the backend reports `completed`; elapsed animation time never completes a task.
- The browser adapter hooks `window.vstUpdateAgentTaskState(snapshot)` and `window.vstClearAgentTaskState(department)` are presentation contracts, not a claim that the current backend already emits task events. Until the production event/API adapter is connected, no real task bars appear.
- If one department is confirmed active and other departments have no confirmed tasks, only the confirmed department gets a progress bar and active workstation visual. Workstation movement is explicitly described as illustrative processing, not market data. Market charts must use real market payloads.
- Zoom controls provide zoom in/out/reset. Department focus blurs non-selected rooms, exposes a focused workstation/progress panel, and provides a direct route to chat with that department's chief. The current prototype routes the conversation to the selected department; it does not yet prove an independent chief agent is deployed.
- Reduced-motion preference disables the workstation animation. The chat-only mode remains available for low-capability devices.
