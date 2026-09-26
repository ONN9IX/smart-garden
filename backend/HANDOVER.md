# Передача Backend Stage 1 разработчику 2

**Рабочая ветка:** `backend/BACK-01-init`.
**Текущий результат:** Backend Stage 1 реализован и проверен в интеграционном PR [#31](https://github.com/ONN9IX/smart-garden/pull/31). Эта ветка содержит тот же каталог `backend/`, чтобы F1zname мог изучить код и продолжить работу. История коммитов показывает фактического автора переноса; назначение роли Backend описано в `docs/08-team-access-and-environments.md`.

## Что прочитать по порядку

1. `../docs/00-development-guide.md` — Git, окружение и порядок работы.
2. `../docs/01-stage-1-backend.md` — требования Stage 1.
3. `../docs/03-api-contract-v0.1.md` — точные URL, JSON и HTTP-коды. Менять его только вместе с Frontend.
4. `../docs/05-personal-data-baseline.md` и `../docs/09-code-and-error-standards.md` — обязательные ограничения.
5. `README.md` в этой папке — команды запуска.

## Карта кода

| Где | Что искать |
| --- | --- |
| `app/main.py` | Создание FastAPI, CORS, контроль Origin, подключение маршрутов, безопасный ответ при непредвиденной ошибке. |
| `app/api/auth.py` | Четыре HTTP endpoint: login, me, change-password, logout; установка и удаление cookie. |
| `app/services/auth.py` | Создание, проверка и отзыв серверных сессий; проверка статуса пользователя и сада. |
| `app/core/security.py` | Нормализация логина, Argon2id для паролей, генерация временного пароля и session token. |
| `app/core/permissions.py` | Проверки роли и принадлежности ресурса текущему саду на Backend. |
| `app/core/errors.py` | Единый JSON ошибок и перевод ошибок валидации в HTTP 400. |
| `app/models/` | Organization, User и AuthSession; все id — UUID. |
| `app/schemas/auth.py` | Формы request/response по API Contract v0.1. |
| `app/db/session.py` и `app/core/config.py` | Соединение с PostgreSQL и параметры из `.env`. |
| `alembic/versions/` | Три миграции: организация → пользователь → сессия. |
| `app/services/seed.py` | Синтетический сад и два demo-аккаунта; временные пароли видны только один раз при создании. |
| `tests/` и `unit_tests/` | Тесты API на PostgreSQL и проверки без БД. |

## Как проходит вход

1. Frontend отправляет `POST /api/v1/auth/login` с username/password. Backend находит пользователя и его организацию, проверяет пароль и статусы.
2. Backend сохраняет **только hash случайного session token** в `auth_sessions`, а сам token отправляет браузеру в `HttpOnly` cookie `smart_garden_session`.
3. `GET /api/v1/auth/me` берёт пользователя и организацию **из сессии**, возвращает роль и `must_change_password`. Frontend направляет пользователя на нужный экран.
4. При временном пароле `POST /api/v1/auth/change-password` сохраняет новый Argon2id hash, отзывает прежние сессии и устанавливает новую cookie.
5. `POST /api/v1/auth/logout` отзывает текущую сессию и удаляет cookie.

Нельзя добавлять во Frontend вторую БД, сохранять session token в JavaScript storage или брать tenant из присланного клиентом `organization_id`.

## Первый локальный запуск (Windows + Git Bash)

Из корня репозитория после переключения на `backend/BACK-01-init`:

```bash
docker compose up -d postgres
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
```

Замените `SECRET_KEY=CHANGE_ME_LOCAL` в **локальном** `.env` на своё случайное значение. Затем в той же папке:

```bash
alembic upgrade head
python -m app.services.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Проверки: `http://localhost:8000/api/v1/health` и `http://localhost:8000/docs`. `seed` покажет временные пароли `director-demo` и `admin-demo` один раз. Не публикуйте их; повторный запуск `seed` не сбрасывает уже созданные пароли. Если Python установлен только как `py`, команды создания окружения можно выполнить через `py -3.12 -m venv .venv`.

## Как убедиться, что ничего не сломано

```bash
ruff check .
pytest -q unit_tests
```

Для полного `pytest` используйте **отдельную тестовую PostgreSQL** и `APP_ENV=test`: тесты выполняют миграции. Не запускайте `alembic downgrade base` на базе с нужными данными: эта команда удаляет таблицы. На синтетическом PostgreSQL 16 в CI прошли 14 тестов Backend, откат/повторное применение миграций и 2 браузерных сценария Frontend ↔ Backend: [результат CI](https://github.com/ONN9IX/smart-garden/actions/runs/36065132798).

## Продолжение работы

- Перед изменением endpoint сверяйте `../docs/03-api-contract-v0.1.md` и согласуйте новое поле или URL с Frontend.
- Следующий продуктовый этап пока описан **примерно** в `../docs/04-mvp-roadmap.md`. Сначала потребуется детальное ТЗ и новый API-контракт для групп, детей и родителей; не добавляйте эти сущности в Stage 1 по своему усмотрению.
- После просмотра и объединения интеграционного PR #31 начинайте следующие задачи от обновлённого `main` в отдельной ветке, как требует `../docs/00-development-guide.md`.

## Персональные данные — обязательный блок

В разработке и тестах используются только синтетические данные. В технических логах не должно быть паролей, временных паролей, cookies, полного auth body и лишних ПДн. Новые таблицы должны иметь tenant context и проверку доступа на Backend; видимость кнопки во Frontend не заменяет эту проверку. Для Stage 2 отдельно определить минимальный набор данных ребёнка/родителя, доступ каждой роли, срок хранения и действия при архивировании. До пилота с реальными данными выполнить требования `../docs/05-personal-data-baseline.md` и юридическую проверку.
