import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import { buildEndpointProofMessage, endpointNonceDigest, parseEndpointProof, verifyEndpointRequest } from "../lib/device-endpoint-proof";

test("verifies a signed endpoint request using the registered Ed25519 public key", () => {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const pem = publicKey.export({ type: "spki", format: "pem" }).toString();
  const message = ["v1", "POST", "/api/v1/devices/endpoint", "publish", "user", "device", "100.100.10.20", "123", "nonce"].join("\n");
  const signature = sign(null, Buffer.from(message), privateKey).toString("base64url");
  assert.equal(verifyEndpointRequest(pem, message, signature), true);
  assert.equal(verifyEndpointRequest(pem, message + "\ntampered", signature), false);
  assert.equal(verifyEndpointRequest(pem, message, signature + "!"), false);
});

test("hashes nonce material before persistence", () => {
  assert.match(endpointNonceDigest("nonce-value"), /^[a-f0-9]{64}$/);
  assert.notEqual(endpointNonceDigest("nonce-value"), endpointNonceDigest("nonce-value-2"));
});

test("accepts a fresh timestamp and well-formed nonce/signature envelope", () => {
  const proof = parseEndpointProof({
    timestamp: Date.now(),
    nonce: "A".repeat(32),
    signature: "A".repeat(86)
  });
  assert.equal(proof.nonce, "A".repeat(32));
});

test("rejects stale timestamps and malformed nonce/signature envelopes", () => {
  assert.throws(() => parseEndpointProof({ timestamp: Date.now() - 300_000, nonce: "A".repeat(32), signature: "A".repeat(86) }), /timestamp_invalid/);
  assert.throws(() => parseEndpointProof({ timestamp: Date.now(), nonce: "short", signature: "A".repeat(86) }), /nonce_invalid/);
  assert.throws(() => parseEndpointProof({ timestamp: Date.now(), nonce: "A".repeat(32), signature: "short" }), /signature_invalid/);
});

test("builds a stable canonical message with newline-delimited signed fields", () => {
  assert.equal(
    buildEndpointProofMessage("user-id", "device-id", 123456, "nonce-value", "publish", "100.100.10.20"),
    "v1\nPOST\n/api/v1/devices/endpoint\npublish\nuser-id\ndevice-id\n100.100.10.20\n123456\nnonce-value"
  );
});
