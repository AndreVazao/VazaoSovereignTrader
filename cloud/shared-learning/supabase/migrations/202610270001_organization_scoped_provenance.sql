-- Organization-scoped identity and shared-artifact provenance registry.
-- This migration defines server-mediated tables only. It does not enroll or approve
-- any organization, installation, agent, or artifact automatically.
create table if not exists public.trader_organizations (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{2,47}$'),
  display_name text not null check (length(trim(display_name)) between 1 and 120),
  status text not null default 'pending' check (status in ('pending','active','suspended','revoked')),
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.trader_organization_memberships (
  organization_id uuid not null references public.trader_organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','admin','publisher','reader')),
  status text not null default 'pending' check (status in ('pending','active','suspended','revoked')),
  created_at timestamptz not null default now(),
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  primary key (organization_id, user_id)
);
create index if not exists trader_org_memberships_user_status_idx
  on public.trader_organization_memberships(user_id, status);

create table if not exists public.trader_installations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.trader_organizations(id) on delete cascade,
  installation_label text not null check (length(trim(installation_label)) between 1 and 120),
  public_key_pem text not null check (length(public_key_pem) between 80 and 8192),
  key_fingerprint text not null check (key_fingerprint ~ '^[a-f0-9]{64}$'),
  status text not null default 'pending' check (status in ('pending','approved','revoked')),
  created_by uuid not null references auth.users(id) on delete restrict,
  approved_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  approved_at timestamptz,
  last_seen_at timestamptz,
  revoked_at timestamptz,
  unique (organization_id, key_fingerprint),
  unique (id, organization_id)
);
create index if not exists trader_installations_org_status_idx
  on public.trader_installations(organization_id, status);

create table if not exists public.trader_departments (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.trader_organizations(id) on delete cascade,
  department_key text not null check (department_key ~ '^[a-z0-9][a-z0-9_-]{1,63}$'),
  display_name text not null check (length(trim(display_name)) between 1 and 80),
  created_at timestamptz not null default now(),
  unique (organization_id, department_key),
  unique (id, organization_id)
);

create table if not exists public.trader_agents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.trader_organizations(id) on delete cascade,
  installation_id uuid not null,
  department_id uuid not null,
  agent_key text not null check (agent_key ~ '^[a-z0-9][a-z0-9_-]{1,63}$'),
  display_name text not null check (length(trim(display_name)) between 1 and 80),
  status text not null default 'active' check (status in ('active','suspended','revoked')),
  created_at timestamptz not null default now(),
  unique (installation_id, agent_key),
  unique (id, organization_id),
  foreign key (installation_id, organization_id)
    references public.trader_installations(id, organization_id) on delete cascade,
  foreign key (department_id, organization_id)
    references public.trader_departments(id, organization_id) on delete restrict
);
create index if not exists trader_agents_org_department_idx
  on public.trader_agents(organization_id, department_id, status);

create table if not exists public.shared_learning_provenance (
  artifact_row_id uuid primary key references public.shared_learning_artifacts(id) on delete cascade,
  organization_id uuid not null references public.trader_organizations(id) on delete restrict,
  installation_id uuid not null,
  agent_id uuid not null,
  department_id uuid not null,
  provenance_schema_version integer not null check (provenance_schema_version = 1),
  payload_digest text not null check (payload_digest ~ '^[a-f0-9]{64}$'),
  signature text not null check (length(signature) between 16 and 2048),
  source_artifact_ids jsonb not null default '[]'::jsonb
    check (jsonb_typeof(source_artifact_ids) = 'array' and jsonb_array_length(source_artifact_ids) <= 32),
  producer_version text not null check (length(trim(producer_version)) between 1 and 64),
  contributed_at timestamptz not null,
  verification_state text not null default 'pending'
    check (verification_state in ('pending','verified','legacy_unverified','quarantined','revoked')),
  verified_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  foreign key (installation_id, organization_id)
    references public.trader_installations(id, organization_id) on delete restrict,
  foreign key (agent_id, organization_id)
    references public.trader_agents(id, organization_id) on delete restrict,
  foreign key (department_id, organization_id)
    references public.trader_departments(id, organization_id) on delete restrict
);
create index if not exists shared_learning_provenance_public_lookup_idx
  on public.shared_learning_provenance(verification_state, contributed_at desc);

-- Access only through server-side routes after auth, membership, installation and signature checks.
do $$
declare t text;
begin
  foreach t in array array[
    'trader_organizations','trader_organization_memberships','trader_installations',
    'trader_departments','trader_agents','shared_learning_provenance'
  ]
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
    execute format('grant all on public.%I to service_role', t);
  end loop;
end $$;
