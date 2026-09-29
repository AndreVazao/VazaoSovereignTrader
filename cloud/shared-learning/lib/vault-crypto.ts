/**
 * Client-side vault encryption helpers.
 *
 * This module must only run on the client/device. The passphrase and derived key
 * are never returned or sent to the server. The cloud stores only the envelope.
 */
export const VAULT_ENCRYPTION_VERSION = 1;
const PBKDF2_ITERATIONS = 310_000;
const SALT_BYTES = 16;
const NONCE_BYTES = 12;
const encoder = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });

export type EncryptedVaultEnvelope = {
  encryption_version: 1;
  algorithm: "AES-GCM";
  kdf: "PBKDF2-SHA-256";
  iterations: number;
  salt: string;
  nonce: string;
  ciphertext: string;
};

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

function base64ToBytes(value: string): Uint8Array {
  if (typeof value !== "string" || value.length > 2_000_000 || !/^[A-Za-z0-9+/]*={0,2}$/.test(value)) {
    throw new Error("invalid_vault_encoding");
  }
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function cryptoApi(): Crypto {
  const api = globalThis.crypto;
  if (!api?.subtle || !api.getRandomValues) throw new Error("secure_crypto_unavailable");
  return api;
}

async function deriveKey(passphrase: string, salt: Uint8Array, iterations: number): Promise<CryptoKey> {
  if (typeof passphrase !== "string" || passphrase.length < 12 || passphrase.length > 1024) {
    throw new Error("vault_passphrase_too_weak");
  }
  const api = cryptoApi();
  const material = await api.subtle.importKey("raw", encoder.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
  return api.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

export async function encryptVaultJson(value: unknown, passphrase: string): Promise<EncryptedVaultEnvelope> {
  const api = cryptoApi();
  const salt = api.getRandomValues(new Uint8Array(SALT_BYTES));
  const nonce = api.getRandomValues(new Uint8Array(NONCE_BYTES));
  const key = await deriveKey(passphrase, salt, PBKDF2_ITERATIONS);
  const plaintext = encoder.encode(JSON.stringify(value));
  if (plaintext.byteLength > 1_000_000) throw new Error("vault_payload_too_large");
  const ciphertext = await api.subtle.encrypt({ name: "AES-GCM", iv: nonce, tagLength: 128 }, key, plaintext);
  return {
    encryption_version: VAULT_ENCRYPTION_VERSION,
    algorithm: "AES-GCM",
    kdf: "PBKDF2-SHA-256",
    iterations: PBKDF2_ITERATIONS,
    salt: bytesToBase64(salt),
    nonce: bytesToBase64(nonce),
    ciphertext: bytesToBase64(new Uint8Array(ciphertext)),
  };
}

export async function decryptVaultJson<T = unknown>(envelope: EncryptedVaultEnvelope, passphrase: string): Promise<T> {
  if (!envelope || envelope.encryption_version !== VAULT_ENCRYPTION_VERSION ||
      envelope.algorithm !== "AES-GCM" || envelope.kdf !== "PBKDF2-SHA-256" ||
      envelope.iterations !== PBKDF2_ITERATIONS) {
    throw new Error("unsupported_vault_envelope");
  }
  const salt = base64ToBytes(envelope.salt);
  const nonce = base64ToBytes(envelope.nonce);
  const ciphertext = base64ToBytes(envelope.ciphertext);
  if (salt.byteLength !== SALT_BYTES || nonce.byteLength !== NONCE_BYTES ||
      ciphertext.byteLength < 16 || ciphertext.byteLength > 1_000_016) {
    throw new Error("invalid_vault_envelope");
  }
  const key = await deriveKey(passphrase, salt, envelope.iterations);
  try {
    const plaintext = await cryptoApi().subtle.decrypt(
      { name: "AES-GCM", iv: nonce, tagLength: 128 }, key, ciphertext,
    );
    return JSON.parse(decoder.decode(plaintext)) as T;
  } catch {
    throw new Error("vault_decryption_failed");
  }
}
