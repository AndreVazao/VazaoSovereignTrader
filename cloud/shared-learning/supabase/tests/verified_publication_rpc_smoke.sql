-- Disposable-database behavioral smoke for the verified publication RPC.
-- All fixture writes are rolled back. Run after applying every migration.
begin;
do $$
declare
  v_owner uuid := '00000000-0000-4000-8000-000000000001';
  v_org uuid := '00000000-0000-4000-8000-000000000002';
  v_installation uuid := '00000000-0000-4000-8000-000000000003';
  v_department uuid := '00000000-0000-4000-8000-000000000004';
  v_agent uuid := '00000000-0000-4000-8000-000000000005';
  v_first jsonb;
  v_duplicate jsonb;
  v_conflict jsonb;
  v_suspended jsonb;
  v_revoked jsonb;
  v_lineage jsonb;
  v_digest text := repeat('a', 64);
begin
  insert into auth.users(id) values (v_owner);
  insert into public.trader_organizations
    (id, slug, display_name, status, created_by, cross_org_visibility)
  values (v_org, 'rpc-smoke-org', 'RPC Smoke Org', 'active', v_owner, 'cross_org_public');
  insert into public.trader_organization_memberships
    (organization_id, user_id, role, status, approved_by, approved_at)
  values (v_org, v_owner, 'publisher', 'active', v_owner, now());
  insert into public.trader_installations
    (id, organization_id, installation_label, public_key_pem, key_fingerprint, status, created_by, approved_by, approved_at)
  values (v_installation, v_org, 'disposable-smoke', repeat('K', 96), repeat('a', 64), 'approved', v_owner, v_owner, now());
  insert into public.trader_departments(id, organization_id, department_key, display_name)
  values (v_department, v_org, 'market-radar', 'Market Radar');
  insert into public.trader_agents
    (id, organization_id, installation_id, department_id, agent_key, display_name, status)
  values (v_agent, v_org, v_installation, v_department, 'radar-chief', 'Radar Chief', 'active');

  v_first := public.publish_verified_shared_learning_artifact(
    v_owner, v_digest, '{"artifact_id":"rpc-smoke-artifact-1","eligible":true}'::jsonb, true,
    now() + interval '1 day', v_org, v_installation, v_agent, v_department, 1, v_digest,
    'signature-test-0001', '[]'::jsonb, 'smoke-1', now());
  if v_first ->> 'ok' <> 'true' then
    raise exception 'first_publication_failed:%', v_first;
  end if;

  v_duplicate := public.publish_verified_shared_learning_artifact(
    v_owner, v_digest, '{"artifact_id":"rpc-smoke-artifact-1","eligible":true}'::jsonb, true,
    now() + interval '1 day', v_org, v_installation, v_agent, v_department, 1, v_digest,
    'signature-test-0001', '[]'::jsonb, 'smoke-1', now());
  if v_duplicate ->> 'ok' <> 'true' then
    raise exception 'idempotent_duplicate_failed:%', v_duplicate;
  end if;
  if (select count(*) from public.shared_learning_artifacts where owner_id = v_owner and artifact_digest = v_digest) <> 1 then
    raise exception 'duplicate_created_multiple_artifacts';
  end if;

  v_conflict := public.publish_verified_shared_learning_artifact(
    v_owner, v_digest, '{"artifact_id":"rpc-smoke-artifact-1","eligible":true}'::jsonb, true,
    now() + interval '1 day', v_org, v_installation, v_agent, v_department, 1, v_digest,
    'signature-test-conflicting', '[]'::jsonb, 'smoke-1', now());
  if v_conflict ->> 'error' <> 'artifact_provenance_conflict' then
    raise exception 'conflicting_duplicate_not_rejected:%', v_conflict;
  end if;

  v_lineage := public.publish_verified_shared_learning_artifact(
    v_owner, repeat('b', 64), '{"artifact_id":"rpc-smoke-artifact-lineage"}'::jsonb, true,
    now() + interval '1 day', v_org, v_installation, v_agent, v_department, 1, repeat('b', 64),
    'signature-test-lineage', '["missing-source"]'::jsonb, 'smoke-1', now());
  if v_lineage ->> 'error' <> 'source_lineage_not_eligible' then
    raise exception 'ineligible_lineage_not_rejected:%', v_lineage;
  end if;

  update public.trader_organization_memberships set status = 'suspended'
   where organization_id = v_org and user_id = v_owner;
  v_suspended := public.publish_verified_shared_learning_artifact(
    v_owner, repeat('c', 64), '{"artifact_id":"rpc-smoke-suspended"}'::jsonb, true,
    now() + interval '1 day', v_org, v_installation, v_agent, v_department, 1, repeat('c', 64),
    'signature-test-suspended', '[]'::jsonb, 'smoke-1', now());
  if v_suspended ->> 'error' <> 'organization_publish_forbidden' then
    raise exception 'suspended_membership_not_rejected:%', v_suspended;
  end if;

  update public.trader_organization_memberships set status = 'active'
   where organization_id = v_org and user_id = v_owner;
  update public.trader_installations set status = 'revoked' where id = v_installation;
  v_revoked := public.publish_verified_shared_learning_artifact(
    v_owner, repeat('d', 64), '{"artifact_id":"rpc-smoke-revoked"}'::jsonb, true,
    now() + interval '1 day', v_org, v_installation, v_agent, v_department, 1, repeat('d', 64),
    'signature-test-revoked', '[]'::jsonb, 'smoke-1', now());
  if v_revoked ->> 'error' <> 'installation_not_approved' then
    raise exception 'revoked_installation_not_rejected:%', v_revoked;
  end if;

  begin
    update public.trader_installations set key_fingerprint = repeat('b', 64) where id = v_installation;
    raise exception 'expected_installation_key_immutability_trigger';
  exception when check_violation then
    if sqlerrm <> 'installation_signing_key_immutable' then raise; end if;
  end;
end $$;
rollback;
select 'verified_publication_rpc_smoke: PASS' as result;