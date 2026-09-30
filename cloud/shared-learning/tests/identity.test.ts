import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync } from "node:crypto";
import { parseDeviceId, parseDeviceRegistration } from "../lib/identity";

test("normalizes a valid device public key and fingerprints the canonical key", () => {
  const { publicKey } = generateKeyPairSync("ed25519");
  const pem = publicKey.export({ type: "spki", format: "pem" }).toString();
  const parsed = parseDeviceRegistration({ label: " André laptop ", public_key: pem });
  assert.equal(parsed.label, "André laptop");
  assert.match(parsed.fingerprint, /^[a-f0-9]{64}$/);
  assert.equal(parsed.publicKey, pem.trim());
});

test("rejects weak RSA and unsupported elliptic curves", () => {
  const weakRsa = generateKeyPairSync("rsa", { modulusLength: 1024 }).publicKey.export({ type: "spki", format: "pem" }).toString();
  const weakEc = generateKeyPairSync("ec", { namedCurve: "secp224r1" }).publicKey.export({ type: "spki", format: "pem" }).toString();
  assert.throws(() => parseDeviceRegistration({ label: "laptop", public_key: weakRsa }), /invalid_device_public_key/);
  assert.throws(() => parseDeviceRegistration({ label: "laptop", public_key: weakEc }), /invalid_device_public_key/);
});

test("accepts approved modern RSA and EC key profiles", () => {
  const rsa = generateKeyPairSync("rsa", { modulusLength: 2048 }).publicKey.export({ type: "spki", format: "pem" }).toString();
  const ec = generateKeyPairSync("ec", { namedCurve: "prime256v1" }).publicKey.export({ type: "spki", format: "pem" }).toString();
  assert.equal(parseDeviceRegistration({ label: "rsa device", public_key: rsa }).fingerprint.length, 64);
  assert.equal(parseDeviceRegistration({ label: "ec device", public_key: ec }).fingerprint.length, 64);
});

test("rejects unknown fields and malformed public keys", () => {
  assert.throws(() => parseDeviceRegistration({ label: "laptop", public_key: "x".repeat(100) }), /invalid_device_public_key/);
  assert.throws(() => parseDeviceRegistration({ label: "laptop", public_key: "x".repeat(100), user_id: "spoof" }), /unknown_device_fields/);
  assert.throws(() => parseDeviceRegistration({ label: "", public_key: "x".repeat(100) }), /invalid_device_label/);
});

test("accepts only UUID device identifiers", () => {
  assert.equal(parseDeviceId("123e4567-e89b-42d3-a456-426614174000"), "123e4567-e89b-42d3-a456-426614174000");
  assert.throws(() => parseDeviceId("not-a-uuid"), /invalid_device_id/);
});
