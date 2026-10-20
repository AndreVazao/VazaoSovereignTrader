# Virtual Office — CEO / Brain Character Reference

## Visual direction

Use the owner-provided photograph from the conversation as the canonical visual reference for the lead human character in the Sovereign Trader virtual office. The character is the CEO / brain: a calm, experienced, approachable executive in a navy suit, white shirt and dark tie, with short grey hair and a grey beard.

## Role and behaviour

- Place the character in the highest-level executive office / command floor.
- The character represents oversight and coordination, not a second trading engine.
- Show only status and activity grounded in the backend's real state/events. Never fabricate trades, transfers, profits, alerts, or agent activity.
- Use the same character design across desktop office, mobile and quality tiers; simplify geometry/textures on weaker devices rather than changing identity.
- Provide an accessible chat-only / compact cockpit fallback; the office must remain optional.
- Keep the character presentation separate from exchange credentials, account secrets and execution authority.

## Asset handling

Canonical future asset location: `virtual_office/assets/characters/ceo-reference.jpg`.

The source photograph is currently present in the conversation upload, but has **not** been committed as a binary repository asset. Do not claim the path above exists until the image is actually added and verified. Once available, derive optimized portrait/thumbnail variants from that source and document any generated derivatives.

## Integration boundary

This is a design reference only. The existing virtual office prototype is still a static demo until connected to live backend events. This change does not alter trading logic, credentials, or execution permissions.
