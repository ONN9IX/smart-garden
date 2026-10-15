#!/usr/bin/env bash
# Read-only local diagnosis and explicit offline owner enrollment/recovery.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

platform_owner_dir=${PLATFORM_OWNER_LOCAL_DIR:-${LOCALAPPDATA:-"$HOME/.local/share"}/SmartGarden/platform-owner}
if command -v cygpath >/dev/null 2>&1; then
  platform_owner_dir=$(cygpath -u "$platform_owner_dir")
fi
platform_owner_env_file=${PLATFORM_OWNER_ENV_FILE:-$platform_owner_dir/platform-owner.env}
if command -v cygpath >/dev/null 2>&1; then
  platform_owner_env_file=$(cygpath -u "$platform_owner_env_file")
fi

compose_args=(--env-file .env.preview)
if [[ -f "$platform_owner_env_file" ]]; then
  compose_args+=(--env-file "$platform_owner_env_file")
fi
compose=(docker compose "${compose_args[@]}" -f docker-compose.yml -f docker-compose.preview.yml)

usage() {
  cat <<'EOF'
Usage:
  bash scripts/setup-platform-owner-local.sh diagnose
  bash scripts/setup-platform-owner-local.sh init-key
  bash scripts/setup-platform-owner-local.sh persist-key EXISTING_USERNAME
  bash scripts/setup-platform-owner-local.sh create USERNAME
  bash scripts/setup-platform-owner-local.sh recover EXISTING_USERNAME

The preview stack must already be running. Key creation is explicit and refused
if any platform operator exists. No command creates a key implicitly.
EOF
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

action=$1
runtime_key_status() {
  "${compose[@]}" exec -T backend python -c '
from app.core.config import get_settings
print("configured" if get_settings().platform_encryption_key else "missing")
'
}

write_new_key() {
  mkdir -p "$platform_owner_dir"
  chmod 700 "$platform_owner_dir"
  temporary_key_file=$(mktemp "$platform_owner_dir/.platform-owner.XXXXXX")
  trap 'rm -f "$temporary_key_file"' EXIT
  "${compose[@]}" exec -T backend python -c '
import os
from cryptography.fernet import Fernet
os.write(1, b"PLATFORM_ENCRYPTION_KEY=" + Fernet.generate_key() + b"\n")
' > "$temporary_key_file"
  chmod 600 "$temporary_key_file"
  if [[ -e "$platform_owner_env_file" ]]; then
    echo 'Key creation refused: config file appeared during setup; generated temporary file removed.' >&2
    exit 1
  fi
  mv "$temporary_key_file" "$platform_owner_env_file"
  trap - EXIT
  compose_args+=(--env-file "$platform_owner_env_file")
  compose=(docker compose "${compose_args[@]}" -f docker-compose.yml -f docker-compose.preview.yml)
}

if [[ "$action" == diagnose ]]; then
  if [[ $# -ne 1 ]]; then usage >&2; exit 2; fi
  echo 'Preview containers:'
  "${compose[@]}" ps --format 'table {{.Service}}\t{{.State}}\t{{.Health}}'
  echo 'Persistent PostgreSQL volume:'
  docker volume ls --filter name=smart_garden_postgres_data --format '{{.Name}}' | sed 's/^/  /'
  echo 'Platform login page:'
  if command -v curl >/dev/null 2>&1; then
    status=$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 5 http://localhost:3000/platform/login || true)
    echo "  http://localhost:3000/platform/login (HTTP ${status:-unavailable})"
  else
    echo '  curl unavailable; check http://localhost:3000/platform/login in a browser.'
  fi
  echo 'Owner identity and MFA state (no credential material):'
  "${compose[@]}" exec -T backend python -c '
from sqlalchemy import select
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.platform_security import decrypt_secret
from app.db.session import SessionLocal
from app.models.platform_operator import PlatformOperator
with SessionLocal() as db:
    rows = db.scalars(select(PlatformOperator).order_by(PlatformOperator.username)).all()
    print(f"  operator count: {len(rows)}")
    for row in rows:
        if not row.totp_secret_ciphertext:
            mfa = "absent"
        elif not get_settings().platform_encryption_key:
            mfa = "configured, key missing"
        else:
            try:
                decrypt_secret(row.totp_secret_ciphertext)
                mfa = "configured, key can decrypt"
            except AppError:
                mfa = "configured, key cannot decrypt"
        print(f"  {row.username}: status={row.status}, MFA={mfa}")
' || {
    echo '  Account state unavailable (backend/database/migration may not be ready).' >&2
    exit 1
  }
  exit 0
fi

if [[ "$action" == init-key ]]; then
  if [[ $# -ne 1 ]]; then usage >&2; exit 2; fi
  if [[ -f "$platform_owner_env_file" ]] || [[ -n "${PLATFORM_ENCRYPTION_KEY:-}" ]]; then
    echo 'Key creation refused: a key is already configured. The current key was not changed.' >&2
    exit 1
  fi
  if [[ "$(runtime_key_status)" != missing ]]; then
    echo 'Key creation refused: the running backend already has an encryption key. Preserve its current source.' >&2
    exit 1
  fi
  count=$("${compose[@]}" exec -T backend python -c '
from sqlalchemy import func, select
from app.db.session import SessionLocal
from app.models.platform_operator import PlatformOperator
with SessionLocal() as db:
    print(db.scalar(select(func.count()).select_from(PlatformOperator)))
')
  if [[ "$count" != 0 ]]; then
    echo "Key creation refused: $count platform operator(s) already exist. Restore the original key; never replace it to fix MFA." >&2
    exit 1
  fi
  write_new_key
  echo "Created a persistent owner key at $platform_owner_env_file (value withheld)."
  echo 'This is safe only because the database currently has no platform operators.'
  exit 0
fi

if [[ "$action" == persist-key ]]; then
  if [[ $# -ne 2 ]]; then usage >&2; exit 2; fi
  if [[ -e "$platform_owner_env_file" ]]; then
    echo 'Key persistence refused: the external config already exists and was not changed.' >&2
    exit 1
  fi
  mkdir -p "$platform_owner_dir"
  chmod 700 "$platform_owner_dir"
  temporary_key_file=$(mktemp "$platform_owner_dir/.platform-owner.XXXXXX")
  trap 'rm -f "$temporary_key_file"' EXIT
  "${compose[@]}" exec -T backend python -c '
import os
import sys
from sqlalchemy import select
from app.core.config import get_settings
from app.core.platform_security import decrypt_secret
from app.db.session import SessionLocal
from app.models.platform_operator import PlatformOperator
try:
    key = get_settings().platform_encryption_key
    with SessionLocal() as db:
        operators = db.scalars(select(PlatformOperator)).all()
        if len(operators) != 1 or operators[0].username != sys.argv[1]:
            raise ValueError
        decrypt_secret(operators[0].totp_secret_ciphertext)
    if not key:
        raise ValueError
except Exception:
    raise SystemExit("Current key or owner precondition failed; no key was exported.") from None
os.write(1, b"PLATFORM_ENCRYPTION_KEY=" + key.encode("ascii") + b"\n")
' "$2" > "$temporary_key_file"
  chmod 600 "$temporary_key_file"
  if [[ -e "$platform_owner_env_file" ]]; then
    echo 'Key persistence refused: config file appeared during setup; temporary copy removed.' >&2
    exit 1
  fi
  mv "$temporary_key_file" "$platform_owner_env_file"
  trap - EXIT
  echo "Persisted the current decryptable key at $platform_owner_env_file (value withheld)."
  echo 'The key was not changed. Restart preview and rerun diagnose to verify the loaded config.'
  exit 0
fi

if [[ "$action" != create && "$action" != recover ]] || [[ $# -ne 2 ]]; then
  usage >&2
  exit 2
fi
username=$2
count=$("${compose[@]}" exec -T backend python -c '
from sqlalchemy import func, select
from app.db.session import SessionLocal
from app.models.platform_operator import PlatformOperator
with SessionLocal() as db:
    print(db.scalar(select(func.count()).select_from(PlatformOperator)))
')
if [[ "$action" == create && "$count" != 0 ]]; then
  echo "Create refused: $count platform operator(s) already exist. Use the existing identity; this command never creates a second owner." >&2
  exit 1
fi
if [[ "$action" == recover ]]; then
  if [[ "$count" != 1 ]]; then
    echo "Recovery refused: expected exactly one existing platform operator, found $count. Diagnose identities; this command does not remove or merge accounts." >&2
    exit 1
  fi
  exists=$("${compose[@]}" exec -T backend python -c '
import sys
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.platform_operator import PlatformOperator
with SessionLocal() as db:
    row = db.scalar(select(PlatformOperator).where(PlatformOperator.username == sys.argv[1]))
    print("yes" if row else "no")
' "$username")
  if [[ "$exists" != yes ]]; then
    echo 'Recovery refused: requested username is not the existing operator.' >&2
    exit 1
  fi
  if [[ "$(runtime_key_status)" == missing ]]; then
    echo 'The key is missing. Continuing will replace it, rotate this operator MFA, and revoke platform sessions.' >&2
    read -r -p "Type LOST-KEY-RECOVERY $username to confirm: " confirmation
    if [[ "$confirmation" != "LOST-KEY-RECOVERY $username" ]]; then
      echo 'Recovery cancelled; no key or account data changed.' >&2
      exit 1
    fi
    write_new_key
  fi
else
  if [[ "$(runtime_key_status)" == missing ]]; then
    echo 'Persistent PLATFORM_ENCRYPTION_KEY is missing. Configure it before creating an operator.' >&2
    exit 1
  fi
fi

mkdir -p "$platform_owner_dir"
chmod 700 "$platform_owner_dir"
enrollment_file=$platform_owner_dir/platform-owner-enrollment.json
if [[ -e "$enrollment_file" ]]; then
  echo "Enrollment file already exists at $enrollment_file; inspect it locally and remove it securely after preserving anything you need. Nothing was overwritten." >&2
  exit 1
fi

echo 'The trusted offline bootstrap will prompt for the password without echoing it.'
if [[ "$action" == recover ]]; then
  echo 'Recovery rotates MFA and revokes existing platform sessions; the previous MFA secret will no longer work.'
fi
"${compose[@]}" run --rm --no-deps \
  --volume "$platform_owner_dir:/run/platform-owner" \
  backend python -m app.services.platform_bootstrap "$action" "$username" \
  --secret-file /run/platform-owner/platform-owner-enrollment.json
echo "Enrollment URI saved outside the repository: $enrollment_file"
echo 'Open it only on this trusted machine, enroll it in your authenticator, then securely remove the file.'
