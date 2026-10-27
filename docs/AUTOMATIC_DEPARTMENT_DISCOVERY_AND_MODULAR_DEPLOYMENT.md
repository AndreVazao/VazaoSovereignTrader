# Automatic Department Discovery and Modular Deployment

**Status:** agreed target architecture; documented, not implemented end to end.
**Scope:** VazaoSovereignTrader (VST) only. DGM-MAT remains separate.

## Owner's requirement

VST is a private, family-only system, not a product intended for sale. Installation should require minimal manual configuration. The owner should not need to visit every computer or enter IP addresses manually to assemble a multi-computer office.

Every VST installation must use Vercel as the rendezvous and registration point so installations belonging to the same owner/organization can discover each other. After discovery, application traffic should travel over the private network: prefer a verified local LAN path when reachable and use Tailscale when needed. Vercel is the discovery/control plane, not a permanent proxy for runtime traffic.

## Core decisions

1. **One codebase and common installer first.** Do not create a separate code fork or mandatory unique build for every department. Produce a generic, versioned installation package and let onboarding select a deployment role. The same package can run all departments on one computer or a selected department/worker set on another computer.
2. **Offer full, custom, and remote-client installation modes.** The setup wizard must let the owner choose (a) Full / all-in-one, (b) Custom / select components, including any supported combination of two, three or more components, or (c) Client-only for a PC/phone that controls a brain running elsewhere. These are modes in one installer, not separate products.
3. **Role-based installation configuration.** Setup offers Full / all-in-one, CEO / coordinator, and department-worker profiles. Role names should come from a versioned registry, not hard-coded installer branches. A role profile controls which services/workers start; it does not create a different product or bypass permissions. The role can be changed later through an authenticated admin flow.
4. **Dependency-aware selection.** The custom screen lists components as selectable items with a short explanation of purpose, estimated disk/resource requirements when known, and required/recommended dependencies. The installer resolves dependencies, tells the user what additional shared services will be installed, and avoids installing the same dependency twice. It must show a final summary before making changes.
5. **Per-host deployment plan.** The wizard configures only the selected host. A user can install the complete system on the home PC and later run the same installer on another computer to add only selected departments. The owner should also be able to add/remove roles later without reinstalling unrelated services, subject to safe migration/backup checks.
6. **Same-host co-location is automatic.** A local supervisor/registry records installation IDs and service instances on that machine. If the CEO and several departments are installed on one PC, they register as local services and use loopback/IPC where appropriate instead of pretending to be remote computers. Multiple department processes on one machine must not collide on ports, storage, logs or identity.
7. **Vercel discovery is always used for registration and peer rendezvous.** Each installation authenticates to the VST discovery service and declares its owner/organization ID, unique installation ID, configured role, agent/departments hosted, protocol/API version, capabilities and health/lease information. It receives the current authorized peer directory for that same owner/organization. It must never discover or join another owner's private organization merely because it shares a LAN.
8. **LAN and Tailscale are transports, not identity.** After discovering peers, clients test eligible private endpoints. Prefer the local LAN endpoint when it is reachable and authenticated; otherwise use the peer's Tailscale endpoint. Re-check reachability and fail over without requiring an operator to copy IPs. Do not assume two devices are on the same LAN merely because discovery returned them.
9. **Vercel is not the normal data plane.** Research records, department messages and runtime/control traffic should flow directly over the authorized private connection after rendezvous. Only registration, discovery, leases, limited health metadata and explicitly designed shared-learning synchronization should use Vercel endpoints. Do not stream market ticks or route all internal traffic through Vercel.
10. **Unique identities and safe pairing.** Each installation receives a stable installation ID and unique agent namespace. A friendly identity may combine owner, host label, role and agent name (for example, “André / PC-Análise / Investigation / Joana”), but display names are not authentication. Pairing must use authenticated, short-lived enrollment, least privilege, revocation, version checks and auditable ownership. Never send API keys, passwords, exchange credentials or private financial state to the discovery service.
11. **Family-only does not mean trust-free.** All installations still require authentication, private-network restrictions, secure secret storage and owner/role isolation. Sharing learned market knowledge does not share balances, credentials, orders, private owner data or REAL-execution authorization.
12. **Discovery outage behavior must be explicit.** A new or not-yet-paired installation cannot silently trust arbitrary peers if Vercel is unavailable. Existing paired installations may use a still-valid, authenticated cached peer directory for a bounded period, if implemented and tested. Stale or revoked peers must fail closed. Never fall back to public Internet exposure.
13. **Role count is not a build matrix.** CI should initially build/test the common runtime and generic installer once per target platform, then test each supported role/profile as configuration variants. Add role-specific artifacts only if a proven difference in dependencies, permissions, resource needs or update lifecycle justifies them. Do not multiply builds just because there are multiple departments.

## Installer wizard: proposed screens

1. **Welcome and existing-install detection:** detect whether this is a fresh install, an update, or adding/changing components on an existing host.
2. **Choose installation mode:**
   - **Full system:** CEO, all supported departments, shared runtime/services, cockpit and virtual office.
   - **Custom components:** multi-select any supported set, such as CEO + Radar + Analysis, or Investigation + Central Memory. Show required dependencies and explain automatically added shared services.
   - **Client only:** cockpit/chat/office client to connect to an already running authorized VST brain on another host; it does not install department workers.
3. **Choose host role and identity:** give the installation a host label and configure its role(s). Use a stable machine installation ID; friendly labels can be edited without changing identity.
4. **Review resources and changes:** summarize components, dependencies, disk space, services, network requirements and any services that will be added/removed. Do not remove a component or its data silently.
5. **Register and pair:** authenticate the owner, register with Vercel, discover authorized peers and show the status of each department. If the discovery service is unavailable, explain which steps cannot safely complete.
6. **Verify:** run local health checks and show installed, connected, missing, incompatible and degraded components separately. Never report the full system as ready just because installation completed.

## Expected installation flow

1. Install the common VST package on a PC.
2. On first launch, setup authenticates the owner and registers this installation with the Vercel discovery service.
3. The owner chooses Full / all-in-one, Custom / selected components, or Client-only. In Custom mode, any supported combination of components is allowed, with dependencies resolved automatically.
4. The local supervisor detects already-running VST services on the same host and avoids duplicate workers, ports and identities. The user can choose whether the new installation should host additional roles or a specific role.
5. The installation announces its role and agent inventory to the owner's VST organization and obtains authorized peers.
6. Peer connection logic checks authenticated LAN endpoints first and Tailscale endpoints as fallback. No manual IP entry is required in the normal case.
7. The installation verifies peer identity, compatible protocol versions and permissions, then reports which departments are connected, missing, stale or unhealthy.
8. If a required department is absent, the CEO/coordinator reports the gap; it must not fabricate a healthy department or mark the system fully ready.
9. Updates use the common versioned release path with staged rollout/rollback and compatibility checks. An update must not change a node's role or owner without explicit authorization.

## Target architecture

- **Vercel discovery/control plane:** owner/organization registry, installation enrollment, role/agent inventory, short-lived peer leases, endpoint candidates, revocation and protocol compatibility. Store the minimum metadata required.
- **Local supervisor on each host:** service lifecycle, host-local installation registry, role configuration, duplicate prevention, health checks, logs and orderly shutdown.
- **VST runtime services:** CEO/coordinator and department workers with authenticated service identities and explicit APIs. All-in-one mode runs these services on one host; distributed mode places them on multiple hosts.
- **Private transport selector:** LAN-first when verified, Tailscale fallback, reconnect/re-discovery, authentication on every transport, bounded retries and clear status.
- **Central learning memory:** initially local to the all-in-one runtime; later it can be assigned to a dedicated memory node. It remains a data service, not an execution-authority service. Concurrent updates need versioning and durable recovery.
- **Client/UI:** cockpit, virtual office and chat are replaceable clients. They do not determine department identity or host the authoritative trading brain.

## Build and release workflow target

- Build a generic Windows installer and Android client as applicable; the phone is normally a control/observation client, not a department host.
- Package role definitions and service manifests as versioned configuration.
- Run automated tests for all-in-one, coordinator-only, each department-worker profile, multiple roles on one host, and distributed roles across simulated hosts.
- Include installation/upgrade/uninstall, rollback, identity uniqueness, discovery registration, peer authentication, LAN-to-Tailscale fallback, service recovery and resource-isolation tests.
- Release a role-specific bundle only when evidence shows that it materially improves dependency isolation, attack surface, resource usage or update management.
- A green build is not proof of physical-network operation. Before readiness claims, run a real PC-to-PC LAN test, a Tailscale remote test, Vercel outage/revocation tests and the physical Android-to-PC control test.

## Acceptance criteria

- The wizard offers Full, Custom multi-select, and Client-only modes.
- Custom mode supports any valid combination of components, resolves dependencies, avoids duplicate shared services and displays a review summary before changes.
- A user can later add/change roles without reinstalling unrelated components, with safe data migration and rollback.
- Two installations for the same owner discover and authenticate each other without manual IP entry.
- An installation belonging to another owner is not visible as an authorized peer and cannot join by sharing the LAN.
- All-in-one mode can host the agreed departments without duplicate service/agent identities.
- A role-specific node starts only the services it is authorized/configured to host.
- LAN is preferred when healthy; Tailscale is selected when LAN is unavailable; transport changes do not weaken authentication.
- Vercel does not carry normal department-to-department traffic or market-tick streams.
- Vercel outage, expired lease, revoked installation, incompatible protocol or invalid authentication results in a clear degraded/blocked status rather than silent trust.
- A missing department is reported honestly, and visual office failure cannot stop the headless runtime.
- No live trading, transfer, withdrawal or REAL-mode activation is permitted as part of install, pairing, discovery or deployment tests.

## Implementation status and next steps

This document records the target architecture only. It does **not** claim that automatic role onboarding, Vercel peer registration, host-local service detection, LAN/Tailscale endpoint selection or department-specific release workflows are complete.

Implementation order:
1. Audit existing Vercel registration, Tailscale and LAN-selection code to reuse the current design and avoid a second discovery system.
2. Define a versioned installation/role manifest and stable installation identity.
3. Add a local supervisor/registry for multiple roles on one host.
4. Integrate authenticated Vercel enrollment and peer leases.
5. Implement/test private endpoint selection and reconnect/failover.
6. Add role-matrix CI and generic release artifacts.
7. Validate real PC-to-PC, remote Tailscale and phone-to-PC behavior before claiming readiness.

All work remains PAPER/read-only. This plan grants no permission to execute live trades or move funds.

## Existing implementation audit (2026-10-27)

The following related components already exist on the active consolidation branch, but they do not yet implement the full organization-wide department discovery described above:

- The mobile client has separate LAN and Tailscale endpoint settings and a pure helper that orders configured endpoints LAN-first. The helper itself performs no network I/O and does not discover peers or fetch endpoints from Vercel.
- The private endpoint lease contract documents a cloud device enrollment flow with Supabase Auth, a per-install keypair, challenge/proof, explicit device approval, and short-lived publication of a private Tailscale endpoint. A published endpoint is routing metadata only; the local PC API must still independently authenticate the peer.
- The Vercel shared-intelligence adapter exchanges allow-listed learning artifacts. It is not an installation registry or peer-discovery service and must not be repurposed as one without a separately reviewed API contract.
- The existing cloud endpoint path is therefore a foundation for secure private endpoint publication, not proof that all PCs register roles, enumerate departments, detect co-located services or automatically establish LAN/Tailscale connections.
- Existing LAN/Tailscale selection documentation is partly a target contract; physical LAN and remote Tailscale end-to-end behavior remains unverified.

### Consequence for implementation

Reuse the existing authenticated cloud-device identity and endpoint-lease design where appropriate, but keep cloud device identity distinct from local owner IDs and local pairing credentials. Define an explicit organization/installation/role registry and peer-directory contract rather than mixing peer discovery into the learning-artifact API. Before wiring clients, verify the deployed Vercel/Supabase routes, current migrations and authentication contract; do not assume a route is deployed or change cloud schema without review.
