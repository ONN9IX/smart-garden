#!/usr/bin/env bash
# Start the full local Stage 1 preview; only synthetic demo users are created.
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

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo 'Нужен запущенный Docker Desktop с Docker Compose.' >&2
  exit 1
fi

if [[ ! -f .env.preview ]]; then
  umask 077
  printf 'SMART_GARDEN_PREVIEW_SECRET_KEY=%s\n' "$(head -c 48 /dev/urandom | base64 | tr -d '\r\n')" > .env.preview
fi

compose_args=(--env-file .env.preview)
if grep -q '^PLATFORM_ENCRYPTION_KEY=.' .env.preview 2>/dev/null; then
  owner_key_available=true
elif [[ -n "${PLATFORM_ENCRYPTION_KEY:-}" ]]; then
  owner_key_available=true
else
  owner_key_available=false
fi
if [[ -f "$platform_owner_env_file" ]]; then
  compose_args+=(--env-file "$platform_owner_env_file")
  if grep -q '^PLATFORM_ENCRYPTION_KEY=.' "$platform_owner_env_file"; then
    owner_key_available=true
  fi
fi
if [[ "$owner_key_available" == false ]]; then
  echo 'PLATFORM_ENCRYPTION_KEY is not configured in the persistent local owner config; platform authentication will fail closed.' >&2
  echo 'Run bash scripts/setup-platform-owner-local.sh diagnose and follow PREVIEW.md before enrolling or recovering an owner.' >&2
elif [[ ! -f "$platform_owner_env_file" ]]; then
  echo 'A platform key is available from another Compose/process environment source. Preserve that exact key and move it to the protected external owner config before relying on restart persistence.' >&2
fi

docker compose "${compose_args[@]}" -f docker-compose.yml -f docker-compose.preview.yml up -d --build --wait --wait-timeout 180

echo 'Демонстрационные пользователи (временные пароли показываются только при первом запуске):'
docker compose "${compose_args[@]}" -f docker-compose.yml -f docker-compose.preview.yml exec -T backend python -m app.services.seed

echo 'Откройте в браузере: http://localhost:3000/login'
echo 'Проверка API: http://localhost:8000/api/v1/health'
