import { createHash, createPublicKey, verify as cryptoVerify } from "node:crypto";

/** Verify a short-lived signed endpoint request. The address is routing metadata, not authority. */
export function verifyEndpointRequest(publicKeyPem: string, message: string, signatureBase64Url: unknown): boolean {
  if (typeof signatureBase64Url !== "string" || !/^[A-Za-z0-9_-]{80,2048}$/.test(signatureBase64Url)) return false;
  try {
    const key = createPublicKey(publicKeyPem);
    const signature = Buffer.from(signatureBase64Url, "base64url");
    if (signature.length < 32 || signature.length > 1024 || signature.toString("base64url") !== signatureBase64Url) return false;
    const algorithm = key.asymmetricKeyType === "ed25519" ? null : "sha256";
    return cryptoVerify(algorithm, Buffer.from(message, "utf8"), key, signature);
  } catch {
    return false;
  }
}
export function endpointNonceDigest(nonce: string): string {
  return createHash("sha256").update(nonce, "utf8").digest("hex");
}
export function parseEndpointProof(value: Record<string, unknown>) {
  const timestamp = value.timestamp;
  const nonce = value.nonce;
  const signature = value.signature;
  if (typeof timestamp !== "number" || !Number.isSafeInteger(timestamp) ||
      Math.abs(Date.now() - timestamp) > 120_000) throw new Error("endpoint_proof_timestamp_invalid");
  if (typeof nonce !== "string" || !/^[A-Za-z0-9_-]{22,128}$/.test(nonce)) throw new Error("endpoint_proof_nonce_invalid");
  if (typeof signature !== "string" || signature.length < 80 || signature.length > 2048) throw new Error("endpoint_proof_signature_invalid");
  return { timestamp, nonce, signature };
}

export function buildEndpointProofMessage(userId: string, deviceId: string, timestamp: number, nonce: string, action: "publish" | "lookup", detail: string): string {
  return ["v1", "POST", "/api/v1/devices/endpoint", action, userId, deviceId, detail, String(timestamp), nonce].join("\n");
}
