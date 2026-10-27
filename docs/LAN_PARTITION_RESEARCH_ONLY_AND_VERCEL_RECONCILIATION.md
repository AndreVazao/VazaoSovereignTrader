# LAN Partition: Research-Only Mode and Vercel Reconciliation

**Status:** architecture contract plus a tested pure policy helper; runtime enforcement is not yet integrated.
**Scope:** VazaoSovereignTrader only. DGM-MAT remains separate.
**Safety:** all development and acceptance tests remain PAPER/read-only. This document does not authorize live trading.

## Decision

Approved work PCs are expected to operate on the same trusted internal network in normal conditions. The LAN is the primary path for peer communication and coordination. Tailscale or another approved private path may be used when the LAN path is unavailable and peer identity is verified. Vercel is a rendezvous/reconciliation point, not a proxy for normal market data or interdepartment traffic.

If a work PC cannot communicate with the required peers over any approved path, it must enter **PARTITIONED_RESEARCH_ONLY**. It may continue bounded, non-authoritative work such as public market research, analysis, local learning, cache refresh and preparing proposed tasks. It must not promote itself to CEO merely because peers are unreachable. It must not perform actions requiring exclusive leadership or issue external side effects that cannot be safely reconciled.

## Connectivity state machine

- **CONNECTED_LAN:** authenticated peer communication works over the internal network; normal permitted coordination.
- **CONNECTED_PRIVATE_OVERLAY:** LAN is unavailable but authenticated communication over the approved private overlay works; normal coordination subject to policy.
- **PARTITIONED_RESEARCH_ONLY:** required peers cannot be reached over approved paths; local research and analysis continue, authority-sensitive operations are blocked, and the supervisor retries discovery with bounded backoff.
- **RECONCILING:** peer connectivity has returned; peers authenticate each other, compare installation identity, current leadership epoch, event cursors, checkpoints and pending task IDs. No automatic replay of external side effects.
- **CONNECTED_DEGRADED:** communication is restored but state is stale, inconsistent or incomplete; research can continue while the supervisor requests repair and blocks affected operations.
- **CONNECTED_LAN / CONNECTED_PRIVATE_OVERLAY:** return to normal coordination only after reconciliation succeeds and a single valid leadership authority is confirmed.

A network timeout is evidence of unreachability, not proof that a host has physically failed. If a configured failure policy permits PC2 or PC3 to promote while isolated, that promotion must be backed by enforceable fencing or an independent quorum/witness; otherwise the candidate remains in research-only mode.

## Reconciliation through Vercel

When communication returns, peers first attempt direct authenticated LAN/private-overlay reconciliation. They also query the Vercel rendezvous/control-plane endpoint, when available, for the latest approved installation roster, revocations, last recorded leader, leadership epoch/grant status and recovery record.

Vercel records are authoritative only for fields actually committed through a durable, authenticated, consistency-safe control-plane transaction. A cached response, stale deployment state, successful HTTP response, or display name is not proof of current leadership.

Reconciliation must:
1. authenticate each installation using its per-install identity; never identify a PC by label alone;
2. compare the current leader and monotonically increasing epoch;
3. mark any returning former leader as fenced/non-authoritative until it synchronizes;
4. compare durable checkpoint versions, event cursors and pending task IDs;
5. deduplicate task events and reconcile external state before considering any retry;
6. share permitted learned knowledge while keeping credentials, balances, orders and private financial state isolated;
7. record a durable outcome and publish actual state changes to the virtual office;
8. remain degraded/research-only if leadership or state cannot be resolved safely.

If Vercel is unavailable but authenticated peers can communicate on the LAN, they may continue normal local work under the existing valid authority and the offline lease policy. They must not invent a new epoch. If the existing authority expires and no safe local fencing/quorum mechanism is available, authority-sensitive work stops until safe coordination returns.

## Leadership and recovery policy

- PC1 is the preferred CEO in the steady-state roster.
- PC2 is the first standby; PC3 is the next standby.
- Priority order selects a candidate but does not itself grant authority.
- A candidate promotes only when its approved identity, health, compatible checkpoint and exclusive authority are verified.
- PC3 cannot preempt a valid PC2 leader.
- When PC1 returns while PC2 leads, PC1 joins as fenced standby. PC2 stays leader during synchronization. Failback is a planned, idempotent handoff with a fresh epoch; PC1 resumes leadership only after the handoff succeeds.
- If safe exclusivity cannot be established, do not elect a new leader. Continue research-only/read-only functions where safe.

## Office observability

The virtual office must display actual connectivity and supervisor events, not infer health from animation. Minimum states: LAN connected, private-overlay connected, partitioned/research-only, reconciling, degraded, leadership confirmed, takeover blocked, host fenced, and failback complete/aborted. Display the last-confirmed timestamp and a reason code when status is stale or unknown.

## Required tests

1. LAN peer loss enters research-only mode and does not promote from timeout alone.
2. Research and local learning continue while authority-sensitive actions are blocked.
3. Approved private-overlay connectivity restores peer communication only after identity validation.
4. Vercel unavailable + LAN healthy allows local coordination under the existing valid authority policy.
5. Vercel available + peers partitioned does not allow both sides to retain accepted authority.
6. Reconnection consults the latest durable roster/epoch and fences a returning old leader.
7. Stale Vercel responses or cached leader records cannot grant authority.
8. Reconciliation deduplicates tasks and does not blindly replay side effects.
9. PC1 returns while PC2 leads and cannot preempt before planned failback.
10. Rendering/office failure does not block the supervisor or research mode.
11. All automated tests assert PAPER/read-only behavior and no live side effects.
12. Physical two-host tests cover LAN switch/router loss, Tailscale failure, Vercel outage, power loss and PC1 rejoin.

## Implementation boundary

Implemented in this PR:
- `PC_ENGINE/core/connectivity_policy.py`: deterministic pure policy for LAN-first, authenticated private-overlay fallback, partitioned research-only, reconciliation and degraded states.
- `tests/test_connectivity_policy.py`: policy tests covering Vercel outage, missing peers, route fallback, rejoin reconciliation and inconsistent state.

Not yet implemented/integrated:
- actual peer health probes and authenticated transport;
- supervisor enforcement of research-only mode at operation boundaries;
- durable host roster, event/checkpoint cursors and epoch reconciliation;
- receiver-side fencing, coordinator/witness semantics, and automatic takeover/failback;
- real office event integration and physical two-host validation.

The pure helper is not a network detector or authority grant. Automatic promotion must remain disabled until receiver-side fencing or a validated quorum mechanism is implemented and tested.
