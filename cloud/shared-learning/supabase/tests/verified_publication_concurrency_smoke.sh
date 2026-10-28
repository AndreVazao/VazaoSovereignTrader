#!/usr/bin/env bash
set -euo pipefail

: "${PGPASSWORD:?PGPASSWORD must be set for disposable PostgreSQL}"
DB_HOST="${PGHOST:-localhost}"
DB_USER="${PGUSER:-postgres}"
DB_NAME="${PGDATABASE:-shared_learning_test}"
psql_base=(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -At)

rpc_call() {
  local digest="$1" artifact_id="$2" signature="$3" sources="${4:-[]}"
  "${psql_base[@]}" -c "
    select case when result->>'ok' = 'true' then 'true' else coalesce(result->>'error', 'false') end
      from (select public.publish_verified_shared_learning_artifact(
        '00000000-0000-4000-8000-000000000001'::uuid,
        '$digest',
        jsonb_build_object('artifact_id', '$artifact_id', 'eligible', true),
        true, now() + interval '1 day',
        '00000000-0000-4000-8000-000000000002'::uuid,
        '00000000-0000-4000-8000-000000000003'::uuid,
        '00000000-0000-4000-8000-000000000005'::uuid,
        '00000000-0000-4000-8000-000000000004'::uuid,
        1, '$digest', '$signature', '$sources'::jsonb, 'concurrency-smoke-1', now()
      ) as result) publication;
  "
}

"${psql_base[@]}" -f cloud/shared-learning/supabase/tests/verified_publication_concurrency_setup.sql

# Two independent sessions publish the same signed artifact concurrently.
digest="$(printf 'e%.0s' {1..64})"
rpc_call "$digest" "rpc-concurrent-artifact-1" "signature-concurrent-0001" '[]' > /tmp/vst-publish-a.txt &
pid_a=$!
rpc_call "$digest" "rpc-concurrent-artifact-1" "signature-concurrent-0001" '[]' > /tmp/vst-publish-b.txt &
pid_b=$!
wait "$pid_a"
wait "$pid_b"
test "$(cat /tmp/vst-publish-a.txt)" = "true"
test "$(cat /tmp/vst-publish-b.txt)" = "true"
artifact_count="$("${psql_base[@]}" -c "select count(*) from public.shared_learning_artifacts where owner_id = '00000000-0000-4000-8000-000000000001' and artifact_digest = '$digest'")"
test "$artifact_count" = "1"

# Race publication against membership suspension. The publication must re-check after its row lock is released.
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL' &
begin;
update public.trader_organization_memberships set status = 'suspended'
 where organization_id = '00000000-0000-4000-8000-000000000002'
   and user_id = '00000000-0000-4000-8000-000000000001';
select pg_sleep(2);
commit;
SQL
suspend_pid=$!
sleep 0.25
suspended_digest="$(printf 'b%.0s' {1..64})"
suspended_result="$(rpc_call "$suspended_digest" "rpc-suspended-race" "signature-suspended-race-0001" '[]')"
wait "$suspend_pid"
echo "suspension-race result: $suspended_result"
if [[ "$suspended_result" != "organization_publish_forbidden" ]]; then
  echo "Expected organization_publish_forbidden after concurrent suspension, got: $suspended_result" >&2
  exit 1
fi

# Restore membership, then race a dependent publication against source-provenance revocation.
"${psql_base[@]}" -c "update public.trader_organization_memberships set status = 'active' where organization_id = '00000000-0000-4000-8000-000000000002' and user_id = '00000000-0000-4000-8000-000000000001'"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL' &
begin;
update public.shared_learning_provenance
   set verification_state = 'revoked', revoked_at = now()
 where artifact_row_id = (
   select id from public.shared_learning_artifacts
    where owner_id = '00000000-0000-4000-8000-000000000001'
      and public_payload->>'artifact_id' = 'rpc-concurrent-artifact-1'
 );
select pg_sleep(2);
commit;
SQL
revoke_pid=$!
sleep 0.25
dependent_digest="$(printf 'f%.0s' {1..64})"
lineage_result="$(rpc_call "$dependent_digest" "rpc-concurrent-dependent" "signature-dependent-0001" '["rpc-concurrent-artifact-1"]')"
wait "$revoke_pid"
echo "lineage-race result: $lineage_result"
if [[ "$lineage_result" != "source_lineage_not_eligible" ]]; then
  echo "Expected source_lineage_not_eligible after concurrent source revocation, got: $lineage_result" >&2
  exit 1
fi

echo "verified_publication_concurrency_smoke: PASS"