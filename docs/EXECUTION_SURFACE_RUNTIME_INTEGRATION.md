# Execution Surface Runtime Integration

The application now owns an explicit PAPER runtime manager at the API layer.

## Lifecycle

Application startup creates `ExecutionSurfaceRuntimeManager`, but this only creates an
in-memory lifecycle container. It does **not** instantiate a browser, desktop process,
ADB connection or APK.

A caller must explicitly:

1. `POST /execution-surfaces/runtime/instantiate` with `runtime_id`, `venue_id` and `surface`.
2. `POST /execution-surfaces/runtime/probe` with `runtime_id` when transport observation is wanted.
3. `POST /execution-surfaces/runtime/close` with `runtime_id` when the instance is no longer wanted.
4. `GET /execution-surfaces/runtime` to inspect actual in-process instances.

Instantiation is inert. Probe is the first operation allowed to touch the configured
transport. This makes `configured`, `registered`, `instantiated` and `observed`
separate states.

## Configuration

The manager accepts an optional `execution_surface.platforms` map for WEB_BROWSER,
DESKTOP_APP and ANDROID_APK. Existing `browser.platforms` entries remain supported for
browser surfaces.

Common persistence defaults are read from `execution_surface.feedback_path` and
`execution_surface.feedback_max_records`. Venue-specific values override those defaults.

## Safety

All runtime adapters remain PAPER-only and observational. The lifecycle API does not
submit orders, persist credentials, bypass readiness, Risk Engine, reconciliation or
`RealModeGuard`, and it never auto-starts a transport.

`probe` is deliberately explicit because it may perform local observation such as opening
the configured browser surface or invoking read-only ADB commands. A successful probe is
transport health evidence only; it is not exchange authentication, economic evidence,
readiness or execution authorization.

The in-memory lifecycle is process-local. After an application restart, no adapter is
claimed to remain instantiated until the caller explicitly instantiates it again.
`GET /execution-surfaces` exposes this distinction in its runtime audit.
