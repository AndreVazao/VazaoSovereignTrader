-- Explicit opt-in policy for cross-organization learning visibility.
-- Existing organizations remain private by default; no data is exposed by this migration.
alter table public.trader_organizations
  add column if not exists cross_org_visibility text not null default 'organization_only';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'trader_organizations_cross_org_visibility_check'
      and conrelid = 'public.trader_organizations'::regclass
  ) then
    alter table public.trader_organizations
      add constraint trader_organizations_cross_org_visibility_check
      check (cross_org_visibility in ('organization_only', 'cross_org_public'));
  end if;
end $$;

create index if not exists trader_organizations_visibility_status_idx
  on public.trader_organizations(status, cross_org_visibility);

comment on column public.trader_organizations.cross_org_visibility is
  'Cross-organization learning visibility. Defaults to organization_only; cross_org_public requires an explicit owner/admin decision.';
