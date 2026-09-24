#!/usr/bin/env bash
# Start the full local Stage 1 preview; only synthetic demo users are created.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo 'Нужен запущенный Docker Desktop с Docker Compose.' >&2
  exit 1
fi

if [[ ! -f .env.preview ]]; then
  umask 077
  printf 'SMART_GARDEN_PREVIEW_SECRET_KEY=%s\n' "$(head -c 48 /dev/urandom | base64 | tr -d '\r\n')" > .env.preview
fi

docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml up -d --build --wait --wait-timeout 180

echo 'Демонстрационные пользователи (временные пароли показываются только при первом запуске):'
docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml exec -T backend python -m app.services.seed

echo 'Откройте в браузере: http://localhost:3000/login'
echo 'Проверка API: http://localhost:8000/api/v1/health'
