import { createHash, createPublicKey, verify as cryptoVerify, type KeyObject } from "node:crypto";

export type DeviceRegistration = { label: string; publicKey: string; fingerprint: string };

export function parseDeviceRegistration(input: unknown): DeviceRegistration {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("invalid_device_payload");
  const value = input as Record<string, unknown>;
  if (Object.keys(value).some((key) => !["label", "public_key"].includes(key))) throw new Error("unknown_device_fields");
  if (typeof value.label !== "string" || value.label.trim().length < 1 || value.label.trim().length > 120) throw new Error("invalid_device_label");
  if (typeof value.public_key !== "string" || value.public_key.length < 80 || value.public_key.length > 8192) throw new Error("invalid_device_public_key");
  let canonical: string;
  try {
    const key = createPublicKey(value.public_key);
    const details = key.asymmetricKeyDetails;
    if (key.asymmetricKeyType === "ed25519") {
      // Ed25519 has a fixed, modern security profile.
    } else if (key.asymmetricKeyType === "rsa") {
      if (!details?.modulusLength || details.modulusLength < 2048) throw new Error("weak_rsa_key");
    } else if (key.asymmetricKeyType === "ec") {
      if (!details?.namedCurve || !["prime256v1", "secp384r1"].includes(details.namedCurve)) throw new Error("weak_or_unsupported_ec_curve");
    } else {
      throw new Error("unsupported_key_type");
    }
    canonical = key.export({ type: "spki", format: "pem" }).toString().trim();
  } catch {
    throw new Error("invalid_device_public_key");
  }
  const fingerprint = createHash("sha256").update(canonical).digest("hex");
  return { label: value.label.trim(), publicKey: canonical, fingerprint };
}

export function verifyDeviceProof(publicKeyPem: string, challenge: string, signatureBase64Url: string): boolean {
  if (challenge.length < 32 || challenge.length > 256) return false;
  if (!/^[A-Za-z0-9_-]{80,2048}$/.test(signatureBase64Url)) return false;
  let key: KeyObject;
  let signature: Buffer;
  try {
    key = createPublicKey(publicKeyPem);
    signature = Buffer.from(signatureBase64Url, "base64url");
    if (signature.length < 32 || signature.length > 1024) return false;
    // Reject non-canonical encodings so malformed inputs cannot be interpreted ambiguously.
    if (signature.toString("base64url") !== signatureBase64Url) return false;
  } catch {
    return false;
  }
  const algorithm = key.asymmetricKeyType === "ed25519" ? null : "sha256";
  try {
    return cryptoVerify(algorithm, Buffer.from(challenge, "utf8"), key, signature);
  } catch {
    return false;
  }
}

export function parseDeviceId(value: string | null): string {
  if (!value || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error("invalid_device_id");
  }
  return value;
}
