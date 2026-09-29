import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const migration = readFileSync(join(process.cwd(), "supabase/migrations/202609290001_identity_devices_vault_config.sql"), "utf8");
const onboarding = readFileSync(join(process.cwd(), "docs/INITIAL_IDENTITY_AND_ONBOARDING.md"), "utf8");

test("reserves the two exact usernames with intended roles only", () => {
  assert.match(migration, /\('AndreVazao', 'André Vazão', 'admin'\)/);
  assert.match(migration, /\('DiogoRocha', 'Diogo Rocha', 'member'\)/);
  assert.match(migration, /create table if not exists public\.reserved_usernames/i);
});

test("does not embed the temporary password or password material in migration", () => {
  assert.doesNotMatch(migration, /123456/);
  assert.doesNotMatch(migration, /password_hash|password_digest|recovery_code/i);
  assert.match(onboarding, /No password, password hash, recovery code, token, or secret belongs in source control/);
});

test("protects identity, device, configuration, vault and audit tables behind server routes", () => {
  for (const table of ["user_profiles", "reserved_usernames", "authorized_devices", "configuration_versions", "encrypted_vault_objects", "security_audit_events"]) {
    assert.match(migration, new RegExp("alter table public\\." + table + " enable row level security", "i"));
    assert.match(migration, new RegExp("revoke all on public\\." + table + " from anon, authenticated", "i"));
  }
});

test("records device approval and config governance states", () => {
  assert.match(migration, /'pending','approved','revoked'/);
  assert.match(migration, /'draft','approved','active','rolled_back','revoked'/);
  assert.match(migration, /ciphertext text not null/);
});
