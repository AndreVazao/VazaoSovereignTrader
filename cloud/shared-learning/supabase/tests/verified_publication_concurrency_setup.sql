-- Fixtures for verified_publication_concurrency_smoke.sh.
-- Use only in the disposable PostgreSQL service created by GitHub Actions.
insert into auth.users(id) values ('00000000-0000-4000-8000-000000000001');
insert into public.trader_organizations
  (id, slug, display_name, status, created_by, cross_org_visibility)
values ('00000000-0000-4000-8000-000000000002', 'rpc-concurrency-org', 'RPC Concurrency Org', 'active',
        '00000000-0000-4000-8000-000000000001', 'cross_org_public');
insert into public.trader_organization_memberships
  (organization_id, user_id, role, status, approved_by, approved_at)
values ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000001',
        'publisher', 'active', '00000000-0000-4000-8000-000000000001', now());
insert into public.trader_installations
  (id, organization_id, installation_label, public_key_pem, key_fingerprint, status, created_by, approved_by, approved_at)
values ('00000000-0000-4000-8000-000000000003', '00000000-0000-4000-8000-000000000002',
        'concurrency-smoke', repeat('K', 96), repeat('a', 64), 'approved',
        '00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000001', now());
insert into public.trader_departments(id, organization_id, department_key, display_name)
values ('00000000-0000-4000-8000-000000000004', '00000000-0000-4000-8000-000000000002', 'market-radar', 'Market Radar');
insert into public.trader_agents
  (id, organization_id, installation_id, department_id, agent_key, display_name, status)
values ('00000000-0000-4000-8000-000000000005', '00000000-0000-4000-8000-000000000002',
        '00000000-0000-4000-8000-000000000003', '00000000-0000-4000-8000-000000000004',
        'radar-chief', 'Radar Chief', 'active');