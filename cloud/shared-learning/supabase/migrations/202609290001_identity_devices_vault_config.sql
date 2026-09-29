-- Identity, device authorization, configuration governance and encrypted vault metadata.
-- Reserved usernames are not accounts and contain no passwords. Provisioning must bind
-- them to verified Supabase Auth identities through a trusted server-side workflow.
create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique check (username ~ '^[A-Za-z0-9]{3,32}$'),
  display_name text not null check (length(display_name) between 1 and 80),
  role text not null default 'member' check (role in ('admin','member')),
  account_state text not null default 'pending' check (account_state in ('pending','active','suspended')),
  must_change_password boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.reserved_usernames (
  username text primary key check (username ~ '^[A-Za-z0-9]{3,32}$'),
  display_name text not null,
  intended_role text not null check (intended_role in ('admin','member')),
  provisioning_state text not null default 'reserved' check (provisioning_state in ('reserved','provisioned','disabled')),
  consumed_by uuid unique references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  provisioned_at timestamptz
);

insert into public.reserved_usernames (username, display_name, intended_role)
values
  ('AndreVazao', 'André Vazão', 'admin'),
  ('DiogoRocha', 'Diogo Rocha', 'member')
on conflict (username) do nothing;

create table if not exists public.authorized_devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  device_public_key text not null,
  device_label text not null check (length(device_label) between 1 and 120),
  device_fingerprint text not null,
  status text not null default 'pending' check (status in ('pending','approved','revoked')),
  approved_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  approved_at timestamptz,
  last_seen_at timestamptz,
  revoked_at timestamptz,
  unique (user_id, device_fingerprint)
);

create table if not exists public.configuration_versions (
  id uuid primary key default gen_random_uuid(),
  scope text not null check (scope in ('global','user')),
  owner_id uuid references auth.users(id) on delete cascade,
  version integer not null check (version > 0),
  config_payload jsonb not null check (jsonb_typeof(config_payload) = 'object'),
  payload_sha256 text not null check (payload_sha256 ~ '^[a-f0-9]{64}$'),
  signature text not null,
  status text not null default 'draft' check (status in ('draft','approved','active','rolled_back','revoked')),
  created_by uuid not null references auth.users(id),
  approved_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  approved_at timestamptz,
  unique (scope, owner_id, version),
  check ((scope = 'global' and owner_id is null) or (scope = 'user' and owner_id is not null))
);
create unique index if not exists configuration_versions_one_active_global
  on public.configuration_versions (scope) where scope = 'global' and status = 'active';
create unique index if not exists configuration_versions_one_active_user
  on public.configuration_versions (owner_id) where scope = 'user' and status = 'active';

create table if not exists public.encrypted_vault_objects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  object_kind text not null check (object_kind in ('profile_backup','selected_config','recovery_bundle')),
  ciphertext text not null,
  encryption_version integer not null check (encryption_version > 0),
  nonce text not null,
  salt text not null,
  ciphertext_sha256 text not null check (ciphertext_sha256 ~ '^[a-f0-9]{64}$'),
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  deleted_at timestamptz
);
create index if not exists encrypted_vault_objects_owner_created_idx
  on public.encrypted_vault_objects (owner_id, created_at desc) where deleted_at is null;

create table if not exists public.security_audit_events (
  id bigint generated always as identity primary key,
  actor_user_id uuid references auth.users(id) on delete set null,
  subject_user_id uuid references auth.users(id) on delete set null,
  event_type text not null check (length(event_type) between 1 and 80),
  outcome text not null check (outcome in ('success','denied','failure')),
  metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
  created_at timestamptz not null default now()
);
create index if not exists security_audit_events_created_idx on public.security_audit_events (created_at desc);

-- All access is mediated by authenticated server routes. Never expose service-role credentials.
do $$
declare t text;
begin
  foreach t in array array['user_profiles','reserved_usernames','authorized_devices','configuration_versions','encrypted_vault_objects','security_audit_events']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
    execute format('grant all on public.%I to service_role', t);
  end loop;
end $$;
