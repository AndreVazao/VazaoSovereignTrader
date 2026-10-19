# Sovereign Trader — Cinematic Virtual Office Introduction

**Status:** product/UX specification  
**Scope:** introduction video and transition into the interactive virtual office  
**Safety boundary:** presentation only; never a source of market, agent, task, or execution truth

## Intent

Create a short cinematic opening that introduces the Sovereign Trader virtual office as a real operational environment. The supplied DGM-MAT image is a visual reference for architecture, lighting, glass-and-steel materials, cyan data pathways, and the sequence from exterior campus to interior workspaces. It is not a request to merge the DGM-MAT product identity or its implementation into Sovereign Trader.

The existing Sovereign Trader introduction video should be treated as the starting point where practical: preserve its own identity, analytical panels, risk framing, and closing signature where compatible. Extend it with a coherent exterior-to-interior camera journey rather than replacing the project identity.

## Proposed sequence

1. **Establish the campus (3–5 seconds).** Aerial dusk view of a modern glass-and-steel research/trading complex. Cyan/blue pathways suggest information flow. Introduce the Sovereign Trader name and restrained ambient sound.
2. **Approach and enter (3–5 seconds).** Camera approaches the main entrance and moves through it. The transition should feel like entering a functioning operations center, not a generic sci-fi montage.
3. **Reveal the central operations floor (4–6 seconds).** Show a central display and a clear view toward connected departments. Use the existing visual language of the Trader's UI.
4. **Visit real departments (6–10 seconds).** Brief, readable shots of exchange data, market/technical research, news and event research, cross-venue comparison, execution-quality analysis, portfolio/risk, and paper validation. Only show departments that exist in the current build or label future capabilities as conceptual.
5. **Land at the command cockpit (3–5 seconds).** Camera arrives at the main operations station; the scene transitions into the actual interactive office UI. The conversational cockpit remains a separate, first-class way to inspect tasks, issue requests, receive alerts, and approve gated actions.

Target duration: approximately 20–30 seconds, adjustable to the existing video's pacing. Avoid fast cuts that make labels unreadable.

## Visual direction

- Architecture: layered glass-and-steel buildings, warm interior lighting, dusk/night exterior, subtle reflections.
- Data pathways: elegant cyan/blue light trails connecting rooms and displays; restrained amber accents for attention or warnings.
- Camera: smooth aerial approach, entrance fly-through, central reveal, short departmental glides, then a stable final shot.
- Typography: legible at desktop and mobile aspect ratios; keep titles short and avoid text baked into generated imagery when it can be rendered cleanly in the video editor.
- Sound: understated technological ambience and a gentle build; no alarm-heavy or arcade-like sound design.
- Identity: Sovereign Trader branding and its own wording only. The DGM-MAT image is inspiration, not a template to copy pixel-for-pixel.

## Truthfulness and operational integrity

The virtual office is a visualization of the system, not the system's brain or source of truth.

- Do not depict agents working, markets being monitored, tasks completing, or trades executing unless the underlying system reports that activity.
- Never use animation as evidence that a feed is connected, a signal is validated, or an order was filled.
- Surface unavailable, stale, disconnected, or unverified states clearly in the interactive UI.
- The opening video may be illustrative, but it must not imply live performance, profitability, or guaranteed trading advantages.
- Keep trading execution, authentication, readiness checks, and risk enforcement independent of the renderer and video.
- Fast execution remains disabled by default and gated by evidence, paper/shadow validation, explicit authorization, and risk controls.

## Runtime and device adaptation

The video is a one-time introduction and must not become a performance cost on every visit. Provide skip/replay controls and remember completion only if the product's privacy and persistence design supports it.

The interactive office must adapt independently:
- **Lite:** low-cost 2D/pixel-art or flat schematic view for weak hardware.
- **Standard:** 2D/2.5D office with navigable departments.
- **High fidelity:** optional 3D environment for capable hardware, with a reliable fallback.
- **Mobile:** compact responsive command/task view; do not force a full 3D scene onto the phone.

Rendering must never reduce market-data freshness, research throughput, risk-engine responsiveness, or reliability. Reduced-motion and reduced-effects modes should be available.

## Implementation phases and acceptance criteria

### Phase A — asset and transition audit
- Review the current Sovereign Trader intro video and identify reusable scenes, typography, branding, and ending.
- Map each proposed shot to either a real existing department or an explicitly conceptual/future department.
- Produce a timed storyboard and shot list before investing in complex animation.

### Phase B — lightweight cinematic prototype
- Build a short exterior-to-command-center prototype using the existing identity.
- Keep a clean transition to the actual office UI; do not pretend the video itself is interactive.
- Confirm readable branding and captions at desktop and portrait/mobile crops.

### Phase C — office handoff
- Opening can be skipped, replayed, and disabled.
- The final transition opens the actual office/cockpit, not a static video frame.
- Department cards and status indicators are driven by actual backend state.
- Disconnected/stale/unknown states are visible; no fabricated agent or market activity.
- Lite mode works without 3D assets and remains responsive on modest hardware.

### Phase D — verification
- Verify playback and skip behavior, reduced motion, aspect ratios, mobile layout, and fallback behavior.
- Profile CPU/GPU/memory with the office running; verify renderer load cannot block critical market or risk tasks.
- Confirm no path from video/UI animation directly to exchange execution.
- Do not claim device/performance validation until tests have actually run.

## Non-goals

- Do not rewrite the trading engine as part of the video task.
- Do not add fictional live prices, performance numbers, exchange connectivity, or agent activity for cinematic effect.
- Do not enable real-money trading as part of the introduction or virtual-office work.
- Do not make 3D mandatory.
