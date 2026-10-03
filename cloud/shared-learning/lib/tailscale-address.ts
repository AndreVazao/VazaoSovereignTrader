import { isIP } from "node:net";

/**
 * Accept only literal addresses in Tailscale's CGNAT IPv4 range or its
 * documented IPv6 ULA prefix. This validates routing metadata only; it is
 * never proof of device identity or permission to connect.
 */
export function parseTailscaleAddress(input: unknown): string {
  if (typeof input !== "string" || input.length < 2 || input.length > 64 || input.trim() !== input) {
    throw new Error("invalid_tailscale_address");
  }

  const family = isIP(input);
  if (family === 4) {
    const octets = input.split(".").map(Number);
    if (octets[0] !== 100 || octets[1] < 64 || octets[1] > 127) {
      throw new Error("tailscale_address_required");
    }
    return input;
  }

  if (family === 6) {
    // Expand a validated IPv6 literal into eight 16-bit groups before checking
    // the /48. Reject IPv4-embedded forms: Tailscale ULA addresses need no them.
    if (input.includes(".")) throw new Error("tailscale_address_required");
    const halves = input.toLowerCase().split("::");
    if (halves.length > 2) throw new Error("invalid_tailscale_address");
    const left = halves[0] ? halves[0].split(":") : [];
    const right = halves.length === 2 && halves[1] ? halves[1].split(":") : [];
    const missing = 8 - left.length - right.length;
    if ((halves.length === 1 && missing !== 0) || (halves.length === 2 && missing < 1)) {
      throw new Error("invalid_tailscale_address");
    }
    const groups = [...left, ...Array(Math.max(0, missing)).fill("0"), ...right];
    if (groups.length !== 8 || groups.some((group) => !/^[0-9a-f]{1,4}$/.test(group))) {
      throw new Error("invalid_tailscale_address");
    }
    if (groups.slice(0, 3).join(":") !== "fd7a:115c:a1e0") {
      throw new Error("tailscale_address_required");
    }
    return input.toLowerCase();
  }

  throw new Error("invalid_tailscale_address");
}
