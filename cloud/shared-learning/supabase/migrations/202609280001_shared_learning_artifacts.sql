create table if not exists public.shared_learning_artifacts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  artifact_digest text not null check (length(artifact_digest) = 64),
  public_payload jsonb not null,
  eligible boolean not null default false,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  constraint shared_learning_artifacts_owner_digest_key unique (owner_id, artifact_digest),
  constraint shared_learning_artifacts_payload_object check (jsonb_typeof(public_payload) = 'object')
);
create index if not exists shared_learning_artifacts_public_expiry_idx
  on public.shared_learning_artifacts (eligible, expires_at desc, created_at desc);
alter table public.shared_learning_artifacts enable row level security;
-- No anon/authenticated table policies: server-side route mediates access after Supabase Auth verification.
-- The service-role key must never be exposed to browser/mobile clients.
revoke all on public.shared_learning_artifacts from anon, authenticated;
grant all on public.shared_learning_artifacts to service_role;
