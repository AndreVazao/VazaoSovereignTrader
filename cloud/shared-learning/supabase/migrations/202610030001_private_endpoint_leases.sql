-- Short-lived, owner-scoped device endpoint announcements.
-- Addresses are routing hints only; this table does not authorize network access.
create unique index if not exists authorized_devices_id_user_id_unique
  on public.authorized_devices(id, user_id);
create table if not exists public.device_endpoint_leases (
  device_id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  foreign key (device_id, user_id) references public.authorized_devices(id, user_id) on delete cascade,
  tailscale_address text not null check (length(tailscale_address) between 2 and 64),
  announced_at timestamptz not null default now(),
  expires_at timestamptz not null,
  check (expires_at > announced_at),
  check (expires_at <= announced_at + interval '10 minutes')
);
create index if not exists device_endpoint_leases_owner_expiry_idx
  on public.device_endpoint_leases(user_id, expires_at desc);
alter table public.device_endpoint_leases enable row level security;
revoke all on public.device_endpoint_leases from public, anon, authenticated;
grant all on public.device_endpoint_leases to service_role;

-- Extend existing per-account rate-limit scopes without changing existing counters.
alter table public.device_security_rate_limits
  drop constraint if exists device_security_rate_limits_scope_check;
alter table public.device_security_rate_limits
  add constraint device_security_rate_limits_scope_check
  check (scope in ('device.register', 'device.challenge', 'device.verify', 'device.approve',
                   'endpoint.publish', 'endpoint.lookup'));

create or replace function public.consume_device_security_rate_limit(
  p_user_id uuid,
  p_scope text,
  p_limit integer,
  p_window_seconds integer
) returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_now timestamptz := clock_timestamp();
  v_count integer;
begin
  if p_user_id is null
     or p_scope is null
     or p_scope not in ('device.register', 'device.challenge', 'device.verify', 'device.approve',
                        'endpoint.publish', 'endpoint.lookup')
     or p_limit is null or p_limit < 1 or p_limit > 120
     or p_window_seconds is null or p_window_seconds < 1 or p_window_seconds > 3600 then
    raise exception 'invalid_rate_limit_parameters';
  end if;

  insert into public.device_security_rate_limits
    (user_id, scope, window_started_at, request_count, updated_at)
  values (p_user_id, p_scope, v_now, 1, v_now)
  on conflict (user_id, scope) do update
    set window_started_at = case
          when public.device_security_rate_limits.window_started_at
               <= v_now - make_interval(secs => p_window_seconds)
          then v_now else public.device_security_rate_limits.window_started_at end,
        request_count = case
          when public.device_security_rate_limits.window_started_at
               <= v_now - make_interval(secs => p_window_seconds)
          then 1 else public.device_security_rate_limits.request_count + 1 end,
        updated_at = v_now
  returning request_count into v_count;

  return v_count <= p_limit;
end;
$$;
revoke all on function public.consume_device_security_rate_limit(uuid, text, integer, integer) from public, anon, authenticated;
grant execute on function public.consume_device_security_rate_limit(uuid, text, integer, integer) to service_role;
