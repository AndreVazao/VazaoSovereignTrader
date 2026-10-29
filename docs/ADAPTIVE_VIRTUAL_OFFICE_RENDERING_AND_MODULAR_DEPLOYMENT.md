# Adaptive Virtual Office Rendering and Modular Deployment

**Status:** adaptive presentation controller is implemented in the HTML prototype; production GPU/3D rendering and process-level resource isolation are not yet implemented. This document separates current behavior from the target architecture.

## Non-negotiable boundary

The Sovereign Trader Runtime is authoritative and headless. The office is a disposable observer/client. Rendering must never own engine state, block a market-data worker, hold risk/order locks, or be required for research, recovery, or safe shutdown. If the office fails or is terminated, the server continues without it.

## Rendering profiles

The same department map and interaction/data contracts must be retained across all profiles. Only presentation changes:

1. **HD / cinematic preview** — selectable CSS presentation profile with stronger contrast/depth effects. This is explicitly a 2D/2.5D preview, not a real WebGL/VR renderer.
2. **Standard 2.5D** — default isometric-lightweight office with room selection.
3. **Pixel / 8-bit** — squared edges, reduced decorative detail and simple shadows.
4. **Stick figures / light** — simplified rooms and reduced animation cost.
5. **Clear rooms / readability** — flatter layout, stronger room boundaries and more readable labels.
6. **Compact / low consumption** — reduced decorative elements and smaller room cards; chat-only remains a separate application mode.

The HTML prototype exposes these CSS presentation profiles in one selector. A real WebGL 3D/VR renderer and cinematic animated 3D characters are not implemented and must not be implied by the cinematic preview label. The underlying department map and runtime contracts remain the same across profiles.

## Automatic device assessment

On startup, the client performs a small, local capability check using information exposed by the platform:
- reduced-motion preference;
- reported device memory, when available;
- reported logical CPU count, when available;
- data-saver preference, when available;
- observed main-thread frame cadence while the tab is visible;
- JavaScript heap pressure where the browser exposes a heap limit and usage.

Initial heuristic: very constrained/reduced-motion devices start in Stick mode; constrained devices start in Pixel mode; others start in Standard 2.5D. Missing browser metrics are treated as unknown, not as proof of high capability.

The selected profile is stored locally per browser installation. Automatic mode chooses a best-effort starting profile from available device hints. A manual selection persists across reloads and is not silently replaced by the automatic recommendation. On constrained devices, the selected profile can keep its identity while decorative effects/animation cadence are reduced; the UI must disclose that reduction. A future native renderer watchdog may ask the operator to switch profiles or disable the scene after sustained severe pressure, but must never change the backend runtime or its safety state. Automatic mode must never upgrade to a heavier profile while the runtime is busy.

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
- Browser tests proving manual selection persists across reloads and is not silently replaced by Automatic; verify resource pressure can reduce effects without changing the selected profile.
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


## Verified task animation and focus navigation

### Truth contract

The office has two distinct visual layers:

1. **Local ambient social life:** a client-side simulation for walking, breaks and informal conversation. It can continue while the backend is unreachable. It must always be labelled as simulation and must not imply backend health or work.
2. **Backend-confirmed work:** progress bars, working posture and active workstation effects are permitted only after a trusted runtime/API adapter validates a task snapshot. The snapshot needs a task ID, agent ID, department, status, progress and update time. An unconfirmed, malformed, stale or disconnected snapshot must remove or visibly mark the task state as unknown; it must never fabricate progress.

A task reaches 100% only on a backend-confirmed completed state. A running task may show only the progress supplied by the backend. If the CEO is the only agent with confirmed work, only the CEO receives work indicators; other characters retain their local ambient routines. A workstation graph animation is only an abstract processing effect and must not be labelled as live market data. Market graphs require actual market-data payloads.

### Navigation and focus

- Provide zoom in, zoom out and reset controls for the office floor.
- Focusing a department reduces the visual prominence of other rooms, presents a focused workstation and task state, and offers a direct chat route to that department.
- The focused conversation targets the department identifier. A named chief-agent identity and independently running agent remain future runtime capabilities until backed by registry/runtime evidence.
- Respect reduced-motion settings and preserve the chat-only fallback on constrained devices.

### Acceptance tests

- No task bar appears without a backend-confirmed task snapshot.
- Only the department named in a validated task snapshot receives work indicators.
- A completed task displays 100% only when status is `completed`.
- Invalid progress, unknown department, missing IDs or an unconfirmed payload never produces a work animation.
- Ambient social animation remains available with no backend connection and is clearly labelled as local simulation.
- Zoom reset returns the floor to 100%; focus dims unrelated rooms and can be exited.
- The chief-chat action selects the same department in the conversation interface.
- Reduced-motion mode disables animated workstation effects.


## Current manual profile selector

The virtual-office prototype now includes a local profile selector with Automatic, Standard 2.5D, Pixel/8-bit, Stick/light, Clear rooms/readability, Cinematic preview (2D/2.5D only) and Compact/low-consumption options. Manual choice is stored in localStorage on the current installation/browser. Automatic uses best-effort device hints (reduced motion, data saver, reported device memory/CPU and viewport width); missing hints are treated as unknown.

Manual choice is not silently overridden by startup heuristics. Profiles only change rendering and do not alter brain scheduling, agent truth state, risk gates, or execution. Compact visual profile and chat-only application mode are separate. The cinematic preview is not a true 3D/VR implementation. Physical PC/Android testing is still required.
