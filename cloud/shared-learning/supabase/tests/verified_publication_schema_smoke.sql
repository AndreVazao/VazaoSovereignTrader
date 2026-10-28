-- Read-only schema/grant smoke checks for a disposable Supabase/Postgres project.
-- Run only after applying all cloud/shared-learning/supabase/migrations/*.sql.
-- Example: psql "$DISPOSABLE_SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f this_file.sql
-- This file intentionally performs no inserts, updates, deletes, or production changes.
do $$
declare
  v_visibility_default text;
  v_rls boolean;
  v_exec_service boolean;
  v_exec_authenticated boolean;
  v_trigger boolean;
begin
  select column_default into v_visibility_default
    from information_schema.columns
   where table_schema = 'public' and table_name = 'trader_organizations'
     and column_name = 'cross_org_visibility';
  if v_visibility_default is null or v_visibility_default not like '%organization_only%' then
    raise exception 'visibility_default_must_be_organization_only';
  end if;

  if not exists (
    select 1 from information_schema.check_constraints cc
    join information_schema.table_constraints tc
      on tc.constraint_name = cc.constraint_name
     and tc.constraint_schema = cc.constraint_schema
   where tc.table_schema = 'public'
     and tc.table_name = 'trader_organizations'
     and tc.constraint_name = 'trader_organizations_cross_org_visibility_check'
     and cc.check_clause like '%organization_only%'
     and cc.check_clause like '%cross_org_public%'
  ) then
    raise exception 'visibility_check_constraint_missing';
  end if;

  foreach v_rls in array array[
    (select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = 'trader_organizations'),
    (select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = 'trader_organization_memberships'),
    (select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = 'trader_installations'),
    (select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = 'trader_departments'),
    (select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = 'trader_agents'),
    (select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = 'shared_learning_provenance'),
    (select c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public' and c.relname = 'shared_learning_artifacts')
  ] loop
    if v_rls is distinct from true then
      raise exception 'rls_not_enabled_on_required_table';
    end if;
  end loop;

  select has_function_privilege(
    'service_role',
    'public.publish_verified_shared_learning_artifact(uuid,text,jsonb,boolean,timestamp with time zone,uuid,uuid,uuid,uuid,integer,text,text,jsonb,text,timestamp with time zone)',
    'EXECUTE'
  ) into v_exec_service;
  select has_function_privilege(
    'authenticated',
    'public.publish_verified_shared_learning_artifact(uuid,text,jsonb,boolean,timestamp with time zone,uuid,uuid,uuid,uuid,integer,text,text,jsonb,text,timestamp with time zone)',
    'EXECUTE'
  ) into v_exec_authenticated;
  if v_exec_service is distinct from true then
    raise exception 'service_role_must_execute_publication_rpc';
  end if;
  if v_exec_authenticated is distinct from false then
    raise exception 'authenticated_must_not_execute_publication_rpc';
  end if;

  select exists (
    select 1 from pg_trigger t
    join pg_class c on c.oid = t.tgrelid
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = 'trader_installations'
      and t.tgname = 'trader_installations_signing_key_immutable'
      and not t.tgisinternal
      and t.tgenabled <> 'D'
  ) into v_trigger;
  if v_trigger is distinct from true then
    raise exception 'immutable_installation_key_trigger_missing_or_disabled';
  end if;

  if has_table_privilege('anon', 'public.shared_learning_artifacts', 'SELECT')
     or has_table_privilege('authenticated', 'public.shared_learning_artifacts', 'SELECT')
     or has_table_privilege('anon', 'public.shared_learning_provenance', 'SELECT')
     or has_table_privilege('authenticated', 'public.shared_learning_provenance', 'SELECT')
     or has_table_privilege('anon', 'public.trader_organizations', 'SELECT')
     or has_table_privilege('authenticated', 'public.trader_organizations', 'SELECT')
     or has_table_privilege('anon', 'public.trader_organization_memberships', 'SELECT')
     or has_table_privilege('authenticated', 'public.trader_organization_memberships', 'SELECT')
     or has_table_privilege('anon', 'public.trader_installations', 'SELECT')
     or has_table_privilege('authenticated', 'public.trader_installations', 'SELECT')
     or has_table_privilege('anon', 'public.trader_departments', 'SELECT')
     or has_table_privilege('authenticated', 'public.trader_departments', 'SELECT')
     or has_table_privilege('anon', 'public.trader_agents', 'SELECT')
     or has_table_privilege('authenticated', 'public.trader_agents', 'SELECT') then
    raise exception 'registry_and_shared_artifacts_must_not_be_directly_readable';
  end if;
end $$;

select 'verified_publication_schema_smoke: PASS' as result;
