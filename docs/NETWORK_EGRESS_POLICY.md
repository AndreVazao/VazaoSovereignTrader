# Operating-System Network Egress Policy (Operator Guide)

## Purpose and boundary

This guide describes how an operator can restrict outbound network access for a dedicated Vazao Sovereign Trader host or test environment. It is guidance only: the application must not silently create, modify, or disable operating-system firewall rules.

The source-ingestion module's HTTPS host/path allowlist and pinned connections constrain that fetch path only. They do not constrain unrelated processes, browser traffic, desktop trading clients, Android emulators, DNS in general, or the host as a whole.

Keep the system in PAPER/read-only mode. Firewall policy is not authorization to place orders, transfer funds, claim rewards, or activate trading automation.

## Before changing policy

1. Use a dedicated test machine or VM where possible; do not start with a production workstation.
2. Ensure you have local/console access and a tested rollback route. Remote-only administration can be disconnected by an incorrect outbound rule.
3. Export or otherwise back up the current firewall policy and record existing network/proxy/VPN/DNS configuration.
4. Identify required destinations by documented operational need: OS updates, endpoint protection, approved source-ingestion endpoints, time synchronization, DNS, VPN/proxy, and any required management services. Do not guess IP addresses from a hostname once and treat them as permanent.
5. Start in audit/monitoring mode where the platform supports it. Review logs before enforcing a deny-by-default policy.
6. Apply changes in small, reversible increments and verify each dependency after each change.

## Windows Defender Firewall

- Review the existing profile state and rules before editing. Use the Windows Defender Firewall with Advanced Security console or an administrator-approved change process.
- Prefer narrowly scoped, named rules tied to the dedicated application executable and required remote endpoints where practical. Document rule owner, purpose, scope, date, and rollback action.
- Windows Firewall rules are not a durable hostname policy in every configuration. Cloud services and CDNs can change IP addresses; use a managed DNS security service, secure web gateway, or network firewall with supported FQDN policy when stable hostname-based control is required.
- Do not blindly switch the default outbound action to Block on a normal workstation. This can interrupt updates, endpoint protection, DNS, VPN, remote management, and unrelated applications.
- Do not disable Defender, endpoint protection, TLS verification, proxy controls, or security monitoring to make connectivity work.

Suggested read-only inspection in an elevated PowerShell session:

```powershell
Get-NetFirewallProfile |
  Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction

Get-NetFirewallRule -PolicyStore ActiveStore |
  Select-Object DisplayName, Enabled, Direction, Action, Profile
```

These commands inspect configuration; they do not prove that a destination is reachable or that the policy is complete. Use your organization's approved logging and connectivity checks to verify a staged change.

## Linux and macOS

- Use the host firewall or centrally managed endpoint/network controls supported by the distribution and organization (for example, nftables/firewalld on Linux or the managed macOS firewall/network-filter stack).
- Review existing policy before adding rules; save a restorable copy and preserve SSH/remote-management access before enforcing outbound restrictions.
- Avoid copying generic deny-all command sequences onto an unknown host. Rule syntax, persistence, VPN routing, DNS handling, IPv6, and package updates vary by system.
- For mixed operating systems, central egress enforcement at a managed gateway or secure DNS/web filtering layer is often easier to audit than maintaining divergent per-host IP lists.

## Verification checklist

- [ ] Existing policy was backed up and a rollback path tested.
- [ ] Required DNS, time, update, endpoint-protection, VPN/proxy, and management paths still work.
- [ ] The approved research fetch path reaches only reviewed public HTTPS endpoints.
- [ ] Redirects to unapproved hosts remain rejected by application tests.
- [ ] IPv4 and IPv6 behavior have been considered; no accidental alternate path bypasses the intended control.
- [ ] Logs show the expected allowed and denied traffic; no broad unexplained allow rule was introduced.
- [ ] Reboot/reconnect behavior has been checked if the rules are persistent.
- [ ] PAPER/read-only behavior remains unchanged and no credentials or platform actions were added.

## Rollback and incident response

If connectivity or endpoint protection breaks, use the documented administrative rollback procedure from local/console access, restore the saved policy, and investigate the rule change. Do not solve failures by globally disabling the firewall or endpoint protection. Record the change and observed results.

## Important limitations

- This guide does not apply any policy to the user's machine and does not include an automatic firewall configurator.
- An application allowlist is not a host-wide firewall. Host firewall rules are not a substitute for secure DNS, network segmentation, least privilege, or endpoint protection.
- A successful connectivity test is not proof that all unauthorized egress is blocked. Verify using logs and an independent network-control review.
- This guide is operational documentation, not a claim that Windows, Linux, or macOS enforcement has been tested in this repository's CI.
