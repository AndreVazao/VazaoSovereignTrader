import test from "node:test";
import assert from "node:assert/strict";
import { canShareAcrossOrganizations } from "../lib/cross-org-visibility";

test("cross-org sharing requires an explicit public opt-in", () => {
  assert.equal(canShareAcrossOrganizations("cross_org_public"), true);
  assert.equal(canShareAcrossOrganizations("organization_only"), false);
  assert.equal(canShareAcrossOrganizations(undefined), false);
  assert.equal(canShareAcrossOrganizations(null), false);
  assert.equal(canShareAcrossOrganizations("legacy"), false);
});
