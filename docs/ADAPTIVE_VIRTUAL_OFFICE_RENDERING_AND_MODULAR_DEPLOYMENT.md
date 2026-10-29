# Adaptive Virtual Office Rendering and Modular Deployment

**Status:** adaptive presentation controller is implemented in the HTML prototype; production GPU/3D rendering and process-level resource isolation are not yet implemented. This document separates current behavior from the target architecture.

## Non-negotiable boundary

The Sovereign Trader Runtime is authoritative and headless. The office is a disposable observer/client. Rendering must never own engine state, block a market-data worker, hold risk/order locks, or be required for research, recovery, or safe shutdown. If the office fails or is terminated, the server continues without it.

## Rendering profiles

The same department map and interaction/data contracts must be retained across all profiles. Only presentation changes:

1. **HD / cinematic 3D** — future optional renderer, enabled only after a real WebGL/GPU implementation and profiling exist. It must not be represented as available in the current HTML prototype.
2. **Standard 2.5D** — isometric lightweight office with room selection.
3. **Pixel / 8-bit** — simplified edges, shadows and effects.
4. **Stick figures** — minimum effects and simplified room rendering.
5. **Compact** — minimum presentation footprint; the chat/control surface remains available if rendering must be disabled entirely.

The current prototype implements CSS-based Standard 2.5D, Pixel, Stick and Compact profiles. It does not yet ship a real WebGL 3D renderer or animated character system. The HD option is intentionally disabled until such a renderer exists.

## Automatic device assessment

On startup, the client performs a small, local capability check using information exposed by the platform:
- reduced-motion preference;
- reported device memory, when available;
- reported logical CPU count, when available;
- data-saver preference, when available;
- observed main-thread frame cadence while the tab is visible;
- JavaScript heap pressure where the browser exposes a heap limit and usage.

Initial heuristic: very constrained/reduced-motion devices start in Stick mode; constrained devices start in Pixel mode; others start in Standard 2.5D. Missing browser metrics are treated as unknown, not as proof of high capability.

During use, repeated slow-frame windows or supported heap pressure automatically reduce the visual profile without asking the operator. The client resets its profile selector to Automatic when it overrides a manual quality selection. The observer should never automatically upgrade to a heavier profile while the runtime is busy. The user may select a lighter profile manually at any time.

Browser metrics are best-effort signals, not a complete measurement of system RAM, GPU memory, CPU saturation or server health. Production desktop clients should add native telemetry where permitted and compare it with server health. Mobile/browser clients must remain safe when these metrics are unavailable.

## Target runtime guard

The production renderer must use a hysteretic budget controller rather than a single threshold:
- sample frame time, renderer memory, process memory, CPU pressure, queue lag and backend scheduling latency;
- degrade after repeated budget breaches, not one isolated frame;
- drop shadows/particles, reduce character count and animation rate, lower render scale, then switch to Pixel, Stick, Compact and finally chat-only;
- pause/offload the visual scene when hidden or disconnected;
- require a sustained healthy period before offering a manual upgrade; never auto-upgrade during active pressure;
- cap event queues and coalesce superseded visual updates;
- keep audit/risk persistence separate from lossy visual events;
- when in doubt, disable the scene, not the engine.

A renderer watchdog must be outside the rendering loop. Rendering errors, a frozen frame, out-of-memory risk or excessive observer queue lag should cause the office process/scene to be restarted or disabled without restarting the trading runtime.


## Ambient social life and department health

The office should retain a small, low-cost visual life even when the backend is stopped or unreachable. In that state, stick figures, pixel agents and future 3D avatars may walk through shared areas, chat, visit the cafeteria, take a short outside break or use the gym. This is a **client-only ambient simulation**: it must be labelled as such and must never imply that the runtime or any department is running. The same underlying activity states and schedules should drive every rendering profile; only the character art and animation fidelity change.

When the backend is connected, real agent work/health states may replace ambient simulation only when supplied by authenticated runtime events or health snapshots. Missing state is “unknown”, not healthy. If the backend reports work but the renderer does not yet implement desk/work animations, the UI must say so rather than pretending that work is visually represented. If there are no confirmed tasks, social idle behaviour may continue.

Add a transversal **Health & Infirmary** service rather than a trading department with authority. The target service performs periodic lightweight heartbeats/check-ups, records last-seen and health status, detects timeouts, raises an alert, and coordinates controlled recovery. A sick-looking character is only a visual mapping of a confirmed degraded/offline state; it must not diagnose by appearance. Recovery should show an agent resting in the infirmary only after the runtime has confirmed isolation/recovery, and return the agent to work only after a successful health check. It must never restart a trading component, clear a risk gate, or replay an order merely because an animation changed.

The initial HTML prototype now includes a lightweight offline-only ambient scene and a selectable Health & Infirmary room. The people, café/gym/exterior activity and conversation bubbles are illustrative CSS animation. They do not represent real agents, actual heartbeat checks, smoking, or backend work. The browser pauses animation for reduced-motion preferences and while the tab is hidden. This is not yet a 3D character system or a production health monitor.

### Health-service acceptance tests

- Backend unavailable: ambient social scene remains visible and explicitly labelled as local simulation.
- Backend connected but health missing: show “unknown”; never mark every department healthy by default.
- A confirmed unhealthy agent gets a timestamped alert and visual degraded state; a timeout alone must not trigger destructive recovery.
- Recovery requires runtime-owned isolation, bounded restart/reconnect policy, a health check and an audit record.
- Successful recovery returns the agent to its normal schedule; persistent failure escalates to the operator.
- Reduced-motion, low-memory and hidden-tab states lower or stop ambient rendering without affecting runtime workers.
- Identical underlying states and activity schedule are preserved across stick, pixel, 2.5D and future 3D renderers.

## Modular deployment model

Keep versioned interfaces between these components so each can move to another machine without redesign:
- **Runtime/server:** market collectors, exchange adapters, research scheduler, risk gates, execution boundary, recovery and audit persistence.
- **Central learning memory:** durable local knowledge store and governed synchronization of validated knowledge only; no exchange credentials, personal account state, balances or private positions by default.
- **Research workers:** independently schedulable modules that publish typed evidence/events through the runtime API or message bus.
- **Virtual office renderer:** optional low-priority client/worker with no authority over runtime state.
- **PC cockpit:** lightweight operator/control client.
- **Android/other phone clients:** authenticated clients only; no requirement to host the main engine.
- **Device registry/rendezvous:** installation identity and discovery metadata; not the trading engine and not a public command relay.

Every install has a unique device/install identity. A client must authenticate and be authorized by the server regardless of whether it is on the same LAN, Tailscale or another host. The runtime binds locally by default; remote access is private-network-only and independently authenticated. A server migration changes endpoint/discovery configuration, not the client contract or the authority model.

## Acceptance tests before release

- Unit tests for profile selection, profile degradation, unknown metrics, reduced motion and repeated threshold breaches.
- Browser tests proving manual quality is overridden when resource pressure persists.
- Tests for tab hiding, reconnect, renderer exception, stale snapshots, queue saturation and backend unavailability.
- Load tests comparing runtime decision/scheduling latency with office off, standard, pixel, stick and saturated clients.
- Verify the office can be killed/restarted without runtime restart, state mutation or order duplication.
- Verify the final fallback is chat-only and does not create a second engine.
- Test on a low-memory physical PC, a GPU-equipped PC, Android emulator and physical phone.
- Do not claim hardware-adaptive production readiness from browser heuristics or static HTML tests alone.

## Current evidence and gaps

Implemented in the prototype:
- user-selectable Automatic, Standard 2.5D, Pixel, Stick and Compact profiles;
- startup heuristics using available browser/device hints;
- runtime frame-cadence monitoring and supported JavaScript heap pressure checks;
- automatic downshift after repeated pressure, including when a manual profile had been selected;
- no network calls or trading-runtime controls in the adaptive rendering controller.

Not yet proven/implemented:
- true GPU/WebGL 3D rendering;
- animated virtual agents with bounded animation budgets;
- native OS/GPU/memory telemetry and process-level resource isolation;
- a renderer worker/process watchdog integrated with the production client;
- end-to-end tests against a running Sovereign Trader backend;
- physical PC and phone measurements.

Until those gaps are closed, treat this as a prototype-level adaptive presentation feature, not a guarantee against all machine-level resource exhaustion.
