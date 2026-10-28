/** Explicit policy gate for cross-organization artifact visibility. */
export type CrossOrgVisibility = "organization_only" | "cross_org_public";

/** Fail closed for missing, unknown, or legacy visibility values. */
export function canShareAcrossOrganizations(value: unknown): value is "cross_org_public" {
  return value === "cross_org_public";
}
