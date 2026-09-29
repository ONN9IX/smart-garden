#!/usr/bin/env bash
# Destructively restore a custom-format backup into an explicit disposable database.
set -euo pipefail

die() {
  printf 'Restore failed: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"
}

require_value() {
  local name="$1"
  [[ -n "${!name:-}" ]] || die "required environment variable is unset: $name"
}

contains_unsafe_text() {
  [[ "$1" =~ [[:space:][:cntrl:]] ]]
}

require_command pg_restore
require_command psql

for variable in PGHOST PGPORT PGUSER BACKUP_FILE RESTORE_DATABASE RESTORE_CONFIRM_DATABASE RESTORE_DISPOSABLE; do
  require_value "$variable"
done

contains_unsafe_text "$PGHOST" && die 'PGHOST contains whitespace or control characters'
contains_unsafe_text "$PGUSER" && die 'PGUSER contains whitespace or control characters'
[[ "$PGUSER" != -* ]] || die 'PGUSER must not begin with a dash'
[[ "$PGPORT" =~ ^[0-9]+$ ]] || die 'PGPORT must be numeric'
port_number=$((10#$PGPORT))
((port_number >= 1 && port_number <= 65535)) || die 'PGPORT is outside the valid range'
[[ ! "$BACKUP_FILE" =~ [[:cntrl:]] ]] || die 'BACKUP_FILE contains control characters'
[[ -f "$BACKUP_FILE" && -s "$BACKUP_FILE" ]] || die 'BACKUP_FILE is missing or empty'

[[ "$RESTORE_DISPOSABLE" == 'YES' ]] || die 'RESTORE_DISPOSABLE=YES is required'
[[ "$RESTORE_CONFIRM_DATABASE" == "$RESTORE_DATABASE" ]] || die 'RESTORE_CONFIRM_DATABASE must exactly match RESTORE_DATABASE'
[[ "$RESTORE_DATABASE" =~ ^smart_garden_recovery_[A-Za-z0-9_]+$ ]] || die 'RESTORE_DATABASE must use the smart_garden_recovery_ disposable prefix'

pg_restore --list "$BACKUP_FILE" >/dev/null || die 'BACKUP_FILE is not a readable pg_restore archive'

printf 'Starting guarded destructive restore into the confirmed disposable database.\n'
pg_restore \
  --no-password \
  --clean \
  --if-exists \
  --exit-on-error \
  --single-transaction \
  --no-owner \
  --no-acl \
  --dbname="$RESTORE_DATABASE" \
  "$BACKUP_FILE"

psql \
  --no-password \
  --no-psqlrc \
  --quiet \
  --set=ON_ERROR_STOP=1 \
  --dbname="$RESTORE_DATABASE" \
  --command='SELECT 1' >/dev/null

printf 'PostgreSQL restore completed and the disposable database is responding.\n'
