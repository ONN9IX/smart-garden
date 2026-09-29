#!/usr/bin/env bash
# Create a PostgreSQL custom-format backup using libpq environment settings.
set -euo pipefail

die() {
  printf 'Backup failed: %s\n' "$1" >&2
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

require_command pg_dump
require_command pg_restore

for variable in PGHOST PGPORT PGUSER PGDATABASE BACKUP_FILE; do
  require_value "$variable"
done

contains_unsafe_text "$PGHOST" && die 'PGHOST contains whitespace or control characters'
contains_unsafe_text "$PGUSER" && die 'PGUSER contains whitespace or control characters'
[[ "$PGUSER" != -* ]] || die 'PGUSER must not begin with a dash'
[[ "$PGDATABASE" =~ ^[A-Za-z_][A-Za-z0-9_.-]*$ ]] || die 'PGDATABASE is not a safe explicit database name'
[[ "$PGPORT" =~ ^[0-9]+$ ]] || die 'PGPORT must be numeric'
port_number=$((10#$PGPORT))
((port_number >= 1 && port_number <= 65535)) || die 'PGPORT is outside the valid range'
[[ ! "$BACKUP_FILE" =~ [[:cntrl:]] ]] || die 'BACKUP_FILE contains control characters'

backup_directory=$(dirname -- "$BACKUP_FILE")
backup_name=$(basename -- "$BACKUP_FILE")
[[ -d "$backup_directory" ]] || die 'BACKUP_FILE parent directory does not exist'
[[ -w "$backup_directory" ]] || die 'BACKUP_FILE parent directory is not writable'
[[ "$backup_name" != '.' && "$backup_name" != '..' ]] || die 'BACKUP_FILE must name a file'

if [[ -e "$BACKUP_FILE" && "${BACKUP_OVERWRITE:-NO}" != 'YES' ]]; then
  die 'BACKUP_FILE already exists; set BACKUP_OVERWRITE=YES to replace it explicitly'
fi

umask 077
temporary_backup=''
cleanup() {
  if [[ -n "$temporary_backup" && -e "$temporary_backup" ]]; then
    rm -f -- "$temporary_backup"
  fi
}
trap cleanup EXIT

temporary_backup=$(mktemp "${backup_directory}/.${backup_name}.tmp.XXXXXX")

pg_dump \
  --no-password \
  --format=custom \
  --compress=6 \
  --no-owner \
  --no-acl \
  --file="$temporary_backup" \
  --dbname="$PGDATABASE"

[[ -s "$temporary_backup" ]] || die 'pg_dump produced an empty backup'
pg_restore --list "$temporary_backup" >/dev/null || die 'pg_restore could not read the backup catalog'

chmod 600 "$temporary_backup"
mv -f -- "$temporary_backup" "$BACKUP_FILE"
temporary_backup=''

[[ -s "$BACKUP_FILE" ]] || die 'completed backup artifact is missing or empty'
printf 'PostgreSQL backup completed and validated.\n'
