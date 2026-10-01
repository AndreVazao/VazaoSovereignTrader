# Execution surface runtime lifecycle

The explicit surface registry identifies the concrete PAPER adapter for each surface. This document defines the next lifecycle boundary without making the registry an execution-authorisation path.

## Lifecycle

1. REGISTERED — a surface has a registered implementation.
2. INSTANTIATED — an explicit caller created the adapter instance.
3. PROBED — an explicit caller invoked the adapter's read-only probe().
4. CLOSED — the explicit runtime instance was closed.
5. PROBE_FAILED — a probe raised an exception; the failure is retained in the runtime snapshot.

Instantiation is intentionally inert. It does not call probe(), observe() or execute(), and therefore does not launch a browser, desktop process or ADB operation.

## Safety boundary

ExecutionSurfaceRuntime is PAPER-only and observational. It exposes no order execution method and never grants execution authority. Future callers that produce execution intents must remain behind the existing readiness, reconciliation, Risk Engine and RealModeGuard controls.

The lifecycle manager does not automatically instantiate configured venues and does not start on application import. Browser, desktop and Android transport activity remains an explicit local runtime action.

The runtime snapshot distinguishes an actual in-process adapter instance from mere registry/configuration evidence. Persisted transport feedback may still be reported separately by the existing feedback store/catalogue.
\n\n## Runtime health and staleness\n\nRuntime health is observational and is derived only from explicit probe feedback. Instantiation alone reports \`NEVER_PROBED\`; it never implies transport health.\n\nThe runtime snapshot exposes:\n\n- \`health\`: \`NEVER_PROBED\`, \`FRESH\`, \`STALE\`, \`PROBE_FAILED\` or \`CLOSED\`;\n- \`stale\`: boolean when a probe timestamp exists, otherwise \`null\`;\n- \`feedback_age_ms\` and \`last_feedback_at_ms\` from the explicit probe feedback;\n- \`health_policy.stale_after_ms\`, configurable with \`execution_surface.runtime_health_stale_after_ms\` (default 30 seconds).\n\nA stale runtime is not automatically probed, restarted, reconnected, or authorized for execution. Recovery remains an explicit operator/application action and a new runtime ID is required after a close because runtime IDs are process-lifetime unique.\n\nRuntime health also does not represent exchange authentication, market-data quality, strategy readiness, reconciliation state, risk approval, or execution authorization. Those remain separate controls.\n