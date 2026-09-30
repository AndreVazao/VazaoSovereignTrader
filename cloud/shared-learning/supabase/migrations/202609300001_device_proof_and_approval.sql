-- One-time proof-of-possession challenges and atomic, audited administrator approval.
alter table public.authorized_devices
  add column if not exists possession_verified_at timestamptz;

create table if not exists public.device_proof_challenges (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid not null references public.authorized_devices(id) on delete cascade,
  challenge_sha256 text not null check (challenge_sha256 ~ '^[a-f0-9]{64}$'),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  consumed_at timestamptz,
  check (expires_at > created_at)
);
create index if not exists device_proof_challenges_owner_expiry_idx
  on public.device_proof_challenges (user_id, expires_at desc);
alter table public.device_proof_challenges enable row level security;
revoke all on public.device_proof_challenges from anon, authenticated;
grant all on public.device_proof_challenges to service_role;

-- The server verifies the active administrator, pending status and prior proof of key possession
-- again inside the database transaction. The audit event and approval update commit atomically.
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
     and status = 'pending'
     and possession_verified_at is not null
   returning user_id into target_user_id;

  if target_user_id is null then
    insert into public.security_audit_events(actor_user_id, event_type, outcome, metadata)
    values (p_actor_user_id, 'device.approval', 'denied', jsonb_build_object('reason', 'device_not_eligible', 'device_id', p_device_id));
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
