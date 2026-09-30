import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const route = readFileSync(join(process.cwd(), "app/api/v1/vault/route.ts"), "utf8");

test("vault route authenticates with server-verified bearer token and active profile", () => {
  assert.match(route, /auth\.auth\.getUser\(token\)/);
  assert.match(route, /account_state === "active" && data\.must_change_password === false/);
});

test("vault writes derive owner from authenticated principal and accept ciphertext envelope only", () => {
  assert.match(route, /owner_id: user\.id/);
  assert.match(route, /unknown_vault_fields/);
  assert.match(route, /ALLOWED_KINDS/);
  assert.match(route, /createHash\("sha256"\)/);
  assert.doesNotMatch(route, /passphrase|decryption_key|exchange_secret/i);
});

test("vault reads, deletes and integrity checks are owner scoped", () => {
  assert.match(route, /\.eq\("id", id\)\.eq\("owner_id", user\.id\)/);
  assert.match(route, /vault_integrity_check_failed/);
  assert.match(route, /deleted_at/);
  assert.match(route, /Cache-Control.*no-store/);
});

test("vault requests are size bounded and expired objects are excluded", () => {
  assert.match(route, /MAX_BODY_BYTES/);
  assert.match(route, /payload_too_large/);
  assert.match(route, /expires_at\.is\.null,expires_at\.gt/);
});
