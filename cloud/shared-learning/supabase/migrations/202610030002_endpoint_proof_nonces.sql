-- Replay protection for signed endpoint announcements and lookups.
create table if not exists public.device_endpoint_request_nonces (
  nonce_sha256 text primary key check (nonce_sha256 ~ '^[a-f0-9]{64}$'),
  user_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid not null,
  foreign key (device_id, user_id) references public.authorized_devices(id, user_id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  check (expires_at > created_at),
  check (expires_at <= created_at + interval '10 minutes')
);
create index if not exists device_endpoint_request_nonces_expiry_idx
  on public.device_endpoint_request_nonces(expires_at);
alter table public.device_endpoint_request_nonces enable row level security;
revoke all on public.device_endpoint_request_nonces from public, anon, authenticated;
grant all on public.device_endpoint_request_nonces to service_role;
