import test from "node:test";
import assert from "node:assert/strict";
import { parseTailscaleAddress } from "../lib/tailscale-address";

test("accepts Tailscale IPv4 addresses in 100.64.0.0/10", () => {
  assert.equal(parseTailscaleAddress("100.64.0.1"), "100.64.0.1");
  assert.equal(parseTailscaleAddress("100.127.255.254"), "100.127.255.254");
});

test("rejects public, LAN, boundary-adjacent and non-literal IPv4 inputs", () => {
  for (const address of ["100.63.255.255", "100.128.0.1", "192.168.1.2", "8.8.8.8", "localhost", "https://100.64.0.1", " 100.64.0.1"]) {
    assert.throws(() => parseTailscaleAddress(address), /invalid_tailscale_address|tailscale_address_required/);
  }
});

test("accepts compressed and expanded Tailscale IPv6 ULA addresses", () => {
  assert.equal(parseTailscaleAddress("fd7a:115c:a1e0::1"), "fd7a:115c:a1e0::1");
  assert.equal(parseTailscaleAddress("fd7a:115c:a1e0:0000:0000:0000:0000:0001"), "fd7a:115c:a1e0:0000:0000:0000:0000:0001");
});

test("rejects other IPv6 prefixes, malformed addresses and URL-shaped input", () => {
  for (const address of ["fc00::1", "fd7a:115c:a1e1::1", "2001:4860:4860::8888", "fd7a:115c:a1e0::1.example", "http://[fd7a:115c:a1e0::1]", "fd7a:115c:a1e0::1.2.3.4"]) {
    assert.throws(() => parseTailscaleAddress(address), /invalid_tailscale_address|tailscale_address_required/);
  }
});
