import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { decryptVaultJson, encryptVaultJson } from "../lib/vault-crypto";

if (!globalThis.crypto?.subtle) {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto, configurable: true });
}

test("vault encryption round-trips without exposing plaintext in the envelope", async () => {
  const value = { profile: "AndreVazao", selected: ["paper-config"], privateNote: "local-only" };
  const envelope = await encryptVaultJson(value, "a-strong-device-vault-passphrase");
  assert.equal(envelope.algorithm, "AES-GCM");
  assert.equal(envelope.kdf, "PBKDF2-SHA-256");
  assert.equal(JSON.stringify(envelope).includes("local-only"), false);
  assert.deepEqual(await decryptVaultJson(envelope, "a-strong-device-vault-passphrase"), value);
});

test("vault decryption fails closed for wrong passphrase or tampered ciphertext", async () => {
  const envelope = await encryptVaultJson({ secret: "private" }, "a-strong-device-vault-passphrase");
  await assert.rejects(
    decryptVaultJson(envelope, "a-different-strong-passphrase"),
    /vault_decryption_failed/,
  );
  const altered = { ...envelope, ciphertext: envelope.ciphertext.slice(0, -4) + "AAAA" };
  await assert.rejects(decryptVaultJson(altered, "a-strong-device-vault-passphrase"));
});

test("vault encryption rejects weak passphrases and unsupported envelopes", async () => {
  await assert.rejects(encryptVaultJson({ ok: true }, "short"), /vault_passphrase_too_weak/);
  const envelope = await encryptVaultJson({ ok: true }, "a-strong-device-vault-passphrase");
  await assert.rejects(
    decryptVaultJson({ ...envelope, iterations: 1 } as typeof envelope, "a-strong-device-vault-passphrase"),
    /unsupported_vault_envelope/,
  );
});
