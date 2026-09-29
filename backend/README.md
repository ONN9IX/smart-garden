# Умный сад — Backend, Stage 1–4 FROZEN

FastAPI + PostgreSQL + SQLAlchemy + Alembic. Реализованы и заморожены Stage 1–4, включая Audit, Announcements и Dashboard. Текущий статус и порядок источников: [`../AGENTS.md`](../AGENTS.md) → [`../docs/CURRENT_STATE.md`](../docs/CURRENT_STATE.md) → контракт текущего Stage → Issue. Frozen HTTP-контракты находятся в `../docs/03-api-contract-v0.1.md`, `../docs/15-api-contract-stage-2.md`, `../docs/20-api-contract-stage-3.md` и `../docs/25-api-contract-stage-4.md`.

[`HANDOVER.md`](HANDOVER.md) — historical Stage 1 handover, а не текущий source of truth.

## Локальный запуск

Требуются Python 3.12+, Docker Compose. Из корня репозитория:

```bash
docker compose up -d postgres
cd backend
python -m venv .venv
# Git Bash/Linux: source .venv/bin/activate; Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Замените SECRET_KEY в локальном .env на своё случайное значение. .env не добавляйте в Git.
alembic upgrade head
python -m app.services.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

`--no-access-log` нужен, чтобы поисковые строки в URL (`q`) не попадали в журнал запросов. При настройке reverse proxy для реальных данных применяйте то же правило к его журналам.

`GET http://localhost:8000/api/v1/health` отвечает `{"status":"ok"}` только при доступном PostgreSQL. OpenAPI — `http://localhost:8000/docs`. Seed-команда создаёт только синтетические demo-аккаунты для Stage 1–4; временный пароль каждого нового пользователя выводится один раз локально. Повторный seed не меняет пароли существующих пользователей. Все прикладные таблицы создаются **только** Alembic.

## Проверки

```bash
ruff check .
pytest
alembic downgrade base
alembic upgrade head
```

Последние две команды выполняйте только на отдельной пустой тестовой БД: `downgrade base` удаляет таблицы и данные. Тесты требуют `DATABASE_URL` для отдельного PostgreSQL и самостоятельно создают/очищают тестовые записи. Они никогда не работают на SQLite.

Для Frontend из `../frontend` установите `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` и запустите `npm run dev` на `localhost:3000`. В Backend `CORS_ORIGINS` должен включать точный origin `http://localhost:3000`.

## Персональные данные

Для разработки используйте только синтетические данные. Пароли хешируются Argon2id; случайные session tokens хранятся в базе только как SHA-256 digest и выдаются браузеру исключительно в `HttpOnly` cookie. Входные данные, cookies и SQL-параметры не логируются; публичные ошибки фиксированного формата. Роль и организация каждого запроса берутся из серверной сессии. Проверки доступа к бизнес-сущностям выполняются на Backend через `require_role`, tenant-scoped queries и действующий API contract. До пилота нужно выполнить задачи из `../docs/05-personal-data-baseline.md`, включая юридическую проверку и требования к размещению.
