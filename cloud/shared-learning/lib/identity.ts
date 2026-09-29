import { createHash, createPublicKey } from "node:crypto";

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
    if (key.asymmetricKeyType !== "ed25519" && key.asymmetricKeyType !== "rsa" && key.asymmetricKeyType !== "ec") throw new Error("unsupported");
    canonical = key.export({ type: "spki", format: "pem" }).toString().trim();
  } catch {
    throw new Error("invalid_device_public_key");
  }
  const fingerprint = createHash("sha256").update(canonical).digest("hex");
  return { label: value.label.trim(), publicKey: canonical, fingerprint };
}

export function parseDeviceId(value: string | null): string {
  if (!value || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error("invalid_device_id");
  }
  return value;
}
