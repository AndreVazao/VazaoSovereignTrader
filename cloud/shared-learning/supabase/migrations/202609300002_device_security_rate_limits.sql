-- Fixed-window, per-account rate limits for device security endpoints.
-- This is a server-side guard, not a substitute for edge/WAF controls or abuse monitoring.
create table if not exists public.device_security_rate_limits (
  user_id uuid not null references auth.users(id) on delete cascade,
  scope text not null check (scope in ('device.challenge', 'device.verify', 'device.approve')),
  window_started_at timestamptz not null,
  request_count integer not null check (request_count > 0),
  updated_at timestamptz not null default now(),
  primary key (user_id, scope)
);
alter table public.device_security_rate_limits enable row level security;
revoke all on public.device_security_rate_limits from public, anon, authenticated;
grant all on public.device_security_rate_limits to service_role;

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
     or p_scope not in ('device.challenge', 'device.verify', 'device.approve')
     or p_limit < 1 or p_limit > 120
     or p_window_seconds < 1 or p_window_seconds > 3600 then
    raise exception 'invalid_rate_limit_parameters';
  end if;

  insert into public.device_security_rate_limits
    (user_id, scope, window_started_at, request_count, updated_at)
  values (p_user_id, p_scope, v_now, 1, v_now)
  on conflict (user_id, scope) do update
    set window_started_at = case
          when public.device_security_rate_limits.window_started_at
               <= v_now - make_interval(secs => p_window_seconds)
          then v_now
          else public.device_security_rate_limits.window_started_at
        end,
        request_count = case
          when public.device_security_rate_limits.window_started_at
               <= v_now - make_interval(secs => p_window_seconds)
          then 1
          else public.device_security_rate_limits.request_count + 1
        end,
        updated_at = v_now
  returning request_count into v_count;

  return v_count <= p_limit;
end;
$$;
revoke all on function public.consume_device_security_rate_limit(uuid, text, integer, integer) from public, anon, authenticated;
grant execute on function public.consume_device_security_rate_limit(uuid, text, integer, integer) to service_role;

-- An administrator cannot approve their own device; another eligible admin must do so.
create or replace function public.approve_authorized_device(p_actor_user_id uuid, p_device_id uuid)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  target_user_id uuid;
begin
  if not exists (
    select 1 from public.user_profiles
    where user_id = p_actor_user_id
      and role = 'admin'
      and account_state = 'active'
      and must_change_password = false
  ) then
    insert into public.security_audit_events(actor_user_id, event_type, outcome, metadata)
    values (p_actor_user_id, 'device.approval', 'denied', jsonb_build_object('reason', 'admin_not_authorized'));
    return false;
  end if;

  update public.authorized_devices
     set status = 'approved', approved_by = p_actor_user_id, approved_at = now()
   where id = p_device_id
     and user_id <> p_actor_user_id
     and status = 'pending'
     and possession_verified_at is not null
   returning user_id into target_user_id;

  if target_user_id is null then
    insert into public.security_audit_events(actor_user_id, event_type, outcome, metadata)
    values (p_actor_user_id, 'device.approval', 'denied',
            jsonb_build_object('reason', 'device_not_eligible', 'device_id', p_device_id));
    return false;
  end if;

  insert into public.security_audit_events(actor_user_id, subject_user_id, event_type, outcome, metadata)
  values (p_actor_user_id, target_user_id, 'device.approval', 'success',
          jsonb_build_object('device_id', p_device_id));
  return true;
end;
$$;
revoke all on function public.approve_authorized_device(uuid, uuid) from public, anon, authenticated;
grant execute on function public.approve_authorized_device(uuid, uuid) to service_role;
