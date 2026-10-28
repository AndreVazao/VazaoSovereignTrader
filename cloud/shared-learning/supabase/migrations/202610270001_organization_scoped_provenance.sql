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
  unique (id, organization_id, installation_id, department_id),
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
  foreign key (agent_id, organization_id, installation_id, department_id)
    references public.trader_agents(id, organization_id, installation_id, department_id) on delete restrict,
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


-- Atomically persist a verified public artifact and its provenance. Signature verification
-- is performed by the API against the approved installation key before this RPC; this
-- function independently re-checks current membership and registry state in the transaction.
create or replace function public.publish_verified_shared_learning_artifact(
  p_owner_id uuid,
  p_artifact_digest text,
  p_public_payload jsonb,
  p_eligible boolean,
  p_expires_at timestamptz,
  p_organization_id uuid,
  p_installation_id uuid,
  p_agent_id uuid,
  p_department_id uuid,
  p_provenance_schema_version integer,
  p_payload_digest text,
  p_signature text,
  p_source_artifact_ids jsonb,
  p_producer_version text,
  p_contributed_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_artifact_id uuid;
  v_existing public.shared_learning_provenance%rowtype;
  v_source_id text;
begin
  if p_artifact_digest !~ '^[a-f0-9]{64}$'
     or p_payload_digest <> p_artifact_digest
     or jsonb_typeof(p_public_payload) <> 'object'
     or jsonb_typeof(p_source_artifact_ids) <> 'array'
     or jsonb_array_length(p_source_artifact_ids) > 32
     or p_expires_at <= now()
     or p_provenance_schema_version <> 1 then
    return jsonb_build_object('ok', false, 'error', 'invalid_publication_payload');
  end if;

  -- Lock authorization rows in this transaction. Revocation/suspension updates
  -- serialize with publication instead of racing between a state check and insert.
  perform 1
    from public.trader_organizations o
    join public.trader_organization_memberships m on m.organization_id = o.id
    where o.id = p_organization_id and o.status = 'active'
      and m.user_id = p_owner_id and m.status = 'active'
      and m.role in ('owner','admin','publisher')
    for update of o, m;
  if not found then
    return jsonb_build_object('ok', false, 'error', 'organization_publish_forbidden');
  end if;

  perform 1
    from public.trader_installations i
    where i.id = p_installation_id and i.organization_id = p_organization_id
      and i.status = 'approved'
    for update;
  if not found then
    return jsonb_build_object('ok', false, 'error', 'installation_not_approved');
  end if;

  perform 1
    from public.trader_agents a
    join public.trader_departments d
      on d.id = a.department_id and d.organization_id = a.organization_id
    where a.id = p_agent_id and a.organization_id = p_organization_id
      and a.installation_id = p_installation_id and a.department_id = p_department_id
      and a.status = 'active'
    for update of a, d;
  if not found then
    return jsonb_build_object('ok', false, 'error', 'agent_department_scope_invalid');
  end if;

  -- Validate and lock every declared source in the same transaction. A signed
  -- list of source IDs is not sufficient: each source must still be public,
  -- eligible, unexpired, verified and backed by active registry identities.
  if exists (
    select 1
      from jsonb_array_elements(p_source_artifact_ids) as item(value)
     where jsonb_typeof(item.value) <> 'string'
        or length(trim(item.value #>> '{}')) = 0
  ) then
    return jsonb_build_object('ok', false, 'error', 'invalid_publication_payload');
  end if;

  if (select count(distinct item.value #>> '{}')
        from jsonb_array_elements(p_source_artifact_ids) as item(value))
       <> jsonb_array_length(p_source_artifact_ids) then
    return jsonb_build_object('ok', false, 'error', 'invalid_publication_payload');
  end if;

  -- Process source IDs in a stable order so concurrent publications with
  -- overlapping lineage sets acquire source-row locks consistently and are
  -- less likely to deadlock solely because callers supplied different array order.
  for v_source_id in
    select item.value #>> '{}'
      from jsonb_array_elements(p_source_artifact_ids) as item(value)
     order by item.value #>> '{}'
  loop
    perform 1
      from public.shared_learning_artifacts source_artifact
      join public.shared_learning_provenance source_provenance
        on source_provenance.artifact_row_id = source_artifact.id
      join public.trader_organizations source_org
        on source_org.id = source_provenance.organization_id
      join public.trader_installations source_installation
        on source_installation.id = source_provenance.installation_id
       and source_installation.organization_id = source_provenance.organization_id
      join public.trader_agents source_agent
        on source_agent.id = source_provenance.agent_id
       and source_agent.organization_id = source_provenance.organization_id
       and source_agent.installation_id = source_provenance.installation_id
       and source_agent.department_id = source_provenance.department_id
      join public.trader_departments source_department
        on source_department.id = source_provenance.department_id
       and source_department.organization_id = source_provenance.organization_id
     where source_artifact.public_payload ->> 'artifact_id' = v_source_id
       and source_artifact.eligible = true
       and source_artifact.expires_at > now()
       and source_provenance.verification_state = 'verified'
       and source_provenance.revoked_at is null
       and source_org.status = 'active'
       and source_org.cross_org_visibility = 'cross_org_public'
       and source_installation.status = 'approved'
       and source_agent.status = 'active'
     for update of source_artifact, source_provenance, source_org,
                   source_installation, source_agent, source_department;
    if not found then
      return jsonb_build_object('ok', false, 'error', 'source_lineage_not_eligible');
    end if;
  end loop;

  insert into public.shared_learning_artifacts (
    owner_id, artifact_digest, public_payload, eligible, expires_at
  ) values (
    p_owner_id, p_artifact_digest, p_public_payload, false, p_expires_at
  )
  on conflict (owner_id, artifact_digest) do nothing
  returning id into v_artifact_id;

  if v_artifact_id is null then
    select id into v_artifact_id
      from public.shared_learning_artifacts
      where owner_id = p_owner_id and artifact_digest = p_artifact_digest
      for update;
  end if;

  select * into v_existing
    from public.shared_learning_provenance
    where artifact_row_id = v_artifact_id
    for update;

  if found then
    if v_existing.organization_id <> p_organization_id
       or v_existing.installation_id <> p_installation_id
       or v_existing.agent_id <> p_agent_id
       or v_existing.department_id <> p_department_id
       or v_existing.payload_digest <> p_payload_digest
       or v_existing.signature <> p_signature
       or v_existing.verification_state <> 'verified'
       or v_existing.revoked_at is not null then
      return jsonb_build_object('ok', false, 'error', 'artifact_provenance_conflict');
    end if;
  else
    insert into public.shared_learning_provenance (
      artifact_row_id, organization_id, installation_id, agent_id, department_id,
      provenance_schema_version, payload_digest, signature, source_artifact_ids,
      producer_version, contributed_at, verification_state, verified_at
    ) values (
      v_artifact_id, p_organization_id, p_installation_id, p_agent_id, p_department_id,
      p_provenance_schema_version, p_payload_digest, p_signature, p_source_artifact_ids,
      p_producer_version, p_contributed_at, 'verified', now()
    );
  end if;

  update public.shared_learning_artifacts
     set eligible = p_eligible, expires_at = p_expires_at
   where id = v_artifact_id;

  return jsonb_build_object('ok', true, 'artifact_row_id', v_artifact_id);
end;
$$;
revoke all on function public.publish_verified_shared_learning_artifact(
  uuid,text,jsonb,boolean,timestamptz,uuid,uuid,uuid,uuid,integer,text,text,jsonb,text,timestamptz
) from public, anon, authenticated;
grant execute on function public.publish_verified_shared_learning_artifact(
  uuid,text,jsonb,boolean,timestamptz,uuid,uuid,uuid,uuid,integer,text,text,jsonb,text,timestamptz
) to service_role;


-- Installation signing keys are immutable after enrollment. Rotate by revoking the
-- old installation and enrolling a new installation/key; this avoids an in-place
-- key replacement racing with API-side signature verification.
create or replace function public.prevent_trader_installation_key_mutation()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
begin
  if new.public_key_pem is distinct from old.public_key_pem
     or new.key_fingerprint is distinct from old.key_fingerprint then
    raise exception 'installation_signing_key_immutable'
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

drop trigger if exists trader_installations_signing_key_immutable
  on public.trader_installations;
create trigger trader_installations_signing_key_immutable
before update of public_key_pem, key_fingerprint
on public.trader_installations
for each row
execute function public.prevent_trader_installation_key_mutation();
