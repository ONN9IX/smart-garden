#!/usr/bin/env bash
# End-to-end recovery verification for a disposable database with synthetic data only.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

die() {
  printf 'Recovery verification failed: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"
}

require_value() {
  local name="$1"
  [[ -n "${!name:-}" ]] || die "required environment variable is unset: $name"
}

for command_name in psql createdb dropdb pg_dump pg_restore alembic; do
  require_command "$command_name"
done

for variable in PGHOST PGPORT PGUSER SOURCE_DATABASE RECOVERY_DATABASE DATABASE_URL RECOVERY_DATABASE_URL APP_ENV RECOVERY_VERIFICATION_SYNTHETIC; do
  require_value "$variable"
done

[[ "$APP_ENV" == 'test' || "$APP_ENV" == 'development' ]] || die 'APP_ENV must be test or development'
[[ "$RECOVERY_VERIFICATION_SYNTHETIC" == 'YES' ]] || die 'RECOVERY_VERIFICATION_SYNTHETIC=YES is required'
[[ "$SOURCE_DATABASE" =~ ^[A-Za-z_][A-Za-z0-9_.-]*$ ]] || die 'SOURCE_DATABASE is not a safe explicit database name'
[[ "$RECOVERY_DATABASE" =~ ^smart_garden_recovery_[A-Za-z0-9_]+$ ]] || die 'RECOVERY_DATABASE must use the smart_garden_recovery_ disposable prefix'
[[ "$SOURCE_DATABASE" != "$RECOVERY_DATABASE" ]] || die 'source and recovery databases must differ'
source_url_without_query="${DATABASE_URL%%\?*}"
recovery_url_without_query="${RECOVERY_DATABASE_URL%%\?*}"
[[ "$source_url_without_query" == */"$SOURCE_DATABASE" ]] || die 'DATABASE_URL must target SOURCE_DATABASE'
[[ "$recovery_url_without_query" == */"$RECOVERY_DATABASE" ]] || die 'RECOVERY_DATABASE_URL must target RECOVERY_DATABASE'

verification_directory=$(mktemp -d)
backup_file="${verification_directory}/smart-garden-recovery.dump"
recovery_created='NO'

cleanup() {
  local exit_status=$?
  trap - EXIT
  set +e
  if [[ "$recovery_created" == 'YES' ]]; then
    PGDATABASE=postgres dropdb \
      --no-password \
      --if-exists \
      --force \
      --maintenance-db=postgres \
      "$RECOVERY_DATABASE" >/dev/null 2>&1
  fi
  rm -f -- "$backup_file"
  rmdir -- "$verification_directory" 2>/dev/null || true
  exit "$exit_status"
}
trap cleanup EXIT

printf 'Checking the synthetic source database.\n'
PGDATABASE="$SOURCE_DATABASE" psql \
  --no-password \
  --no-psqlrc \
  --quiet \
  --set=ON_ERROR_STOP=1 \
  --command='SELECT 1' >/dev/null

# Add deterministic Stage 4 evidence using only existing synthetic seed identities.
PGDATABASE="$SOURCE_DATABASE" psql \
  --no-password \
  --no-psqlrc \
  --quiet \
  --set=ON_ERROR_STOP=1 <<'SQL'
INSERT INTO announcements (
    id, organization_id, target_type, group_id, title, body, status,
    created_by, updated_by
)
SELECT
    '00000000-0000-4000-8000-000000000104'::uuid,
    organization.id,
    'all',
    NULL,
    'Stage 4 recovery verification',
    'Synthetic CI record for PostgreSQL backup and restore verification.',
    'active',
    actor.id,
    actor.id
FROM organizations AS organization
JOIN users AS actor ON actor.organization_id = organization.id
WHERE organization.name = 'Детский сад «Солнышко»'
  AND actor.username = 'stage4-director-demo'
ON CONFLICT (id) DO NOTHING;

INSERT INTO audit_events (
    id, organization_id, actor_user_id, action, entity_type, entity_id, details
)
SELECT
    '00000000-0000-4000-8000-000000000103'::uuid,
    organization.id,
    actor.id,
    'announcement.created',
    'announcement',
    '00000000-0000-4000-8000-000000000104'::uuid,
    '{"target_type":"all","verification":"synthetic-recovery"}'::jsonb
FROM organizations AS organization
JOIN users AS actor ON actor.organization_id = organization.id
WHERE organization.name = 'Детский сад «Солнышко»'
  AND actor.username = 'stage4-director-demo'
ON CONFLICT (id) DO NOTHING;
SQL

verify_synthetic_records() {
  local database_name="$1"
  PGDATABASE="$database_name" psql \
    --no-password \
    --no-psqlrc \
    --quiet \
    --set=ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
    IF (SELECT count(*) FROM organizations) <> 2
       OR EXISTS (
           SELECT 1 FROM organizations
           WHERE name NOT IN ('Детский сад «Солнышко»', 'Синтетический сад другого tenant')
       )
       OR NOT EXISTS (
           SELECT 1 FROM users
           WHERE username = 'director-demo' AND role = 'DIRECTOR'
       ) THEN
        RAISE EXCEPTION 'Stage 1 synthetic recovery evidence is incomplete';
    END IF;

    IF (SELECT count(*) FROM users) <> 7
       OR EXISTS (
           SELECT 1 FROM users
           WHERE username NOT IN (
               'director-demo', 'admin-demo', 'stage2-director-demo',
               'stage3-director-demo', 'stage3-other-director-demo',
               'stage4-director-demo', 'stage4-other-director-demo'
           )
       ) THEN
        RAISE EXCEPTION 'unexpected non-synthetic users are present';
    END IF;

    IF (SELECT count(*) FROM groups) <> 1
       OR (SELECT count(*) FROM children) <> 1
       OR (SELECT count(*) FROM guardians) <> 1
       OR (SELECT count(*) FROM child_guardians) <> 1
       OR NOT EXISTS (
           SELECT 1 FROM groups WHERE name = 'Ромашка' AND status = 'active'
       )
       OR NOT EXISTS (
           SELECT 1 FROM children
           WHERE first_name = 'Тестовый' AND last_name = 'Ребёнок'
       )
       OR NOT EXISTS (
           SELECT 1 FROM guardians
           WHERE first_name = 'Тестовый' AND last_name = 'Представитель'
       )
       OR NOT EXISTS (SELECT 1 FROM child_guardians) THEN
        RAISE EXCEPTION 'Stage 2 synthetic recovery evidence is incomplete';
    END IF;

    IF (SELECT count(*) FROM employees) <> 1
       OR (SELECT count(*) FROM attendance) <> 2
       OR NOT EXISTS (
           SELECT 1 FROM employees
           WHERE first_name = 'Тестовая' AND last_name = 'Сотрудница'
       )
       OR NOT EXISTS (
           SELECT 1 FROM attendance
           WHERE date = DATE '2025-09-20' AND status = 'present'
       )
       OR NOT EXISTS (
           SELECT 1 FROM attendance
           WHERE date = DATE '2025-09-21' AND status = 'absent'
       ) THEN
        RAISE EXCEPTION 'Stage 3 synthetic recovery evidence is incomplete';
    END IF;

    IF (SELECT count(*) FROM announcements) <> 1
       OR (SELECT count(*) FROM audit_events) <> 1
       OR NOT EXISTS (
           SELECT 1 FROM announcements
           WHERE id = '00000000-0000-4000-8000-000000000104'::uuid
             AND title = 'Stage 4 recovery verification'
             AND status = 'active'
       )
       OR NOT EXISTS (
           SELECT 1 FROM audit_events
           WHERE id = '00000000-0000-4000-8000-000000000103'::uuid
             AND action = 'announcement.created'
             AND details->>'verification' = 'synthetic-recovery'
       ) THEN
        RAISE EXCEPTION 'Stage 4 synthetic recovery evidence is incomplete';
    END IF;
END
$$;
SQL
}

verify_synthetic_records "$SOURCE_DATABASE"

printf 'Creating and validating a PostgreSQL custom-format backup.\n'
PGDATABASE="$SOURCE_DATABASE" \
BACKUP_FILE="$backup_file" \
scripts/backup-postgres.sh
[[ -s "$backup_file" ]] || die 'backup artifact is missing or empty'
pg_restore --list "$backup_file" >/dev/null || die 'backup artifact catalog cannot be read'

printf 'Creating the disposable recovery database.\n'
PGDATABASE=postgres dropdb \
  --no-password \
  --if-exists \
  --force \
  --maintenance-db=postgres \
  "$RECOVERY_DATABASE" >/dev/null
PGDATABASE=postgres createdb \
  --no-password \
  --maintenance-db=postgres \
  --owner="$PGUSER" \
  "$RECOVERY_DATABASE"
recovery_created='YES'

printf 'Restoring into the disposable recovery database.\n'
BACKUP_FILE="$backup_file" \
RESTORE_DATABASE="$RECOVERY_DATABASE" \
RESTORE_CONFIRM_DATABASE="$RECOVERY_DATABASE" \
RESTORE_DISPOSABLE=YES \
scripts/restore-postgres.sh

actual_head=$(PGDATABASE="$RECOVERY_DATABASE" psql \
  --no-password \
  --no-psqlrc \
  --tuples-only \
  --no-align \
  --set=ON_ERROR_STOP=1 \
  --command='SELECT version_num FROM alembic_version')
mapfile -t repository_heads < <((cd backend && alembic heads) | awk '{print $1}')
[[ "${#repository_heads[@]}" -eq 1 ]] || die 'repository must have exactly one Alembic head'
expected_head="${repository_heads[0]}"
[[ -n "$actual_head" && "$actual_head" == "$expected_head" ]] || die 'restored database is not at the current Alembic head'

printf 'Checking restored migration compatibility.\n'
(cd backend && DATABASE_URL="$RECOVERY_DATABASE_URL" alembic upgrade head >/dev/null)
post_upgrade_head=$(PGDATABASE="$RECOVERY_DATABASE" psql \
  --no-password \
  --no-psqlrc \
  --tuples-only \
  --no-align \
  --set=ON_ERROR_STOP=1 \
  --command='SELECT version_num FROM alembic_version')
[[ "$post_upgrade_head" == "$expected_head" ]] || die 'Alembic compatibility verification changed or lost the expected head'

printf 'Checking representative restored Stage 1-4 synthetic records.\n'
verify_synthetic_records "$RECOVERY_DATABASE"

printf 'Cleaning disposable recovery resources.\n'
PGDATABASE=postgres dropdb \
  --no-password \
  --if-exists \
  --force \
  --maintenance-db=postgres \
  "$RECOVERY_DATABASE" >/dev/null || die 'could not drop the disposable recovery database'
recovery_created='NO'
rm -f -- "$backup_file" || die 'could not remove the temporary backup artifact'
rmdir -- "$verification_directory" || die 'could not remove the temporary verification directory'
trap - EXIT

printf 'Disposable PostgreSQL backup and recovery verification passed.\n'
