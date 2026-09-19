# Clock & Latency Calibration

## Purpose

Measure timing reality before the Lead/Lag engine treats one venue as earlier
than another. Browser render delay is never treated as a market lead by itself.

## Time domains

The trader keeps three distinct concepts:

1. Venue/provider epoch time — timestamps supplied by the exchange/provider.
2. Local wall-clock epoch time — captured at message receipt so venue time can
   be compared with the machine clock.
3. Local monotonic time — used for elapsed intervals and local processing delay;
   it must never be directly subtracted from epoch time.

The calibration layer reports median clock offset, p95/p99 offset, robust jitter
around the median, median local processing delay, and per-venue isolation.

## Interpretation

A positive offset means the local wall clock is later than the venue timestamp
by the measured amount. This is an observation, not proof that the machine
clock is globally correct.

The system must not claim NTP/PTP-grade synchronization unless an independent
clock-synchronization measurement exists.

## Operational rule

Lead/lag decisions should prefer exchange event time, then provider event time,
then calibrated local receipt time, while retaining raw timestamps for
audit/replay.

If a venue does not provide an event timestamp, the collector can still record
local receive time, but cross-venue event-time claims must carry lower confidence
until independently calibrated.

## Safety

This phase is observational only. It does not create orders, allocate capital,
or enable REAL mode.
