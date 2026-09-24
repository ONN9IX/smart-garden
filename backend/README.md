# Умный сад — Backend, этап 1

FastAPI + PostgreSQL + SQLAlchemy + Alembic. HTTP-контракт: `../docs/03-api-contract-v0.1.md`.

Новому разработчику: начните с [HANDOVER.md](HANDOVER.md) — там карта файлов, сценарий входа и порядок проверки.

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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`GET http://localhost:8000/api/v1/health` отвечает `{"status":"ok"}` только при доступном PostgreSQL. OpenAPI — `http://localhost:8000/docs`. У seed-команды синтетические `director-demo` и `admin-demo`; временный пароль каждого нового пользователя выводится один раз локально. Повторный seed не меняет пароли существующих пользователей. Все прикладные таблицы создаются **только** Alembic.

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

Для разработки используйте только синтетические данные. Пароли хешируются Argon2id; случайные session tokens хранятся в базе только как SHA-256 digest и выдаются браузеру исключительно в `HttpOnly` cookie. Входные данные, cookies и SQL-параметры не логируются; публичные ошибки фиксированного формата. Роль и организация каждого запроса берутся из серверной сессии. Проверки доступа к будущим сущностям используют `require_role` и `require_tenant`. До пилота нужно выполнить задачи из `../docs/05-personal-data-baseline.md`, включая юридическую проверку и требования к размещению.
