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

export function parseDeviceId(value: string | null): string {
  if (!value || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error("invalid_device_id");
  }
  return value;
}
