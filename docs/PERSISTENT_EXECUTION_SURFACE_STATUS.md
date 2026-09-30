# Persistent execution surface status

This layer persists adapter feedback locally for operational dashboard telemetry.

## What it exposes

- execution surface and venue;
- transport/connection state;
- operational classification: HEALTHY, DEGRADED, DOWN;
- age of the last feedback;
- reconnect transitions observed in the bounded retained history;
- local feedback write health;
- source (persistent_feedback vs configuration fallback).

The persistence is bounded and written atomically. It is not a trading ledger and does not infer profitability, OOS quality, risk approval or REAL authorization.

## PAPER safety

Every persisted record is forced to paper_only=true, orders_submitted=false and execution_authorized=false.

The browser adapter can opt into persistence through PlaywrightPaperConfig.feedback_path. No order control is clicked and no private API is invoked.

## Configuration

The dashboard catalogue reads execution_surface.feedback_path (default PC_ENGINE/data/execution/surface_feedback.jsonl), execution_surface.feedback_max_records (default 2000), and execution_surface.feedback_stale_after_ms (default 30000).

No cloud storage or paid service is required.

## Interpretation

A healthy transport only means that the configured surface is responding and producing fresh feedback. It does not mean the venue is economically attractive, the strategy is profitable, or that execution is authorized.

The next concrete surfaces can reuse the same store through Desktop and Android adapters, including local Windows bridges and ADB/emulator flows. Human interaction remains available when authentication, MFA or other interactive steps require it.
