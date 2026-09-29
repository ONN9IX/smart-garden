# Умный сад — MVP 0.1

Репозиторий первого MVP SaaS-системы для частных детских садов.

## С чего начинать разработчику

Перед любой задачей читайте источники в таком порядке:

1. [`AGENTS.md`](AGENTS.md) — обязательные правила репозитория и Fast Flow.
2. [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — фактический frozen baseline и текущий gate.
3. Контракт текущего Stage.
4. Текущую GitHub Issue.

**Проверка Stage 4 в браузере:** [PREVIEW.md](PREVIEW.md) — запуск Frontend, Backend и PostgreSQL одной командой с синтетическими аккаунтами.

[`docs/00-development-guide.md`](docs/00-development-guide.md) сохраняет общую архитектуру, Git-процесс и исторические bootstrap-инструкции Stage 1. Frontend и Backend не являются отдельными продуктами: Frontend работает только через Backend API, а единственная БД MVP — PostgreSQL на Backend.

Локальная среда и доступы должны быть воспроизводимыми без передачи личных паролей.

## Текущий фокус

Stage 1–4 реализованы, приняты и FROZEN. Stage 5 NOT STARTED и может начаться только с отдельного design/planning gate после решения Master Chat. СКУД/планшет на входе, платежи, AI, фото и сложные интеграции пока не входят в разработку.

### Этап 1 — фундамент (FROZEN)
- Backend: организация, пользователи, роли, авторизация по логину/паролю, временный пароль, смена пароля, изоляция данных организаций.
- Frontend: каркас приложения, login, обязательная смена временного пароля, защищённые маршруты, базовый layout, role-aware UI.
- Общий результат: DIRECTOR и ADMIN могут безопасно войти в систему и попасть в интерфейс своего сада.

### Этап 2 (FROZEN)
- Группы
- Дети
- Родители / законные представители
- Создание PARENT-аккаунта
- Связь одного родителя с несколькими детьми

### Этап 3 (FROZEN)
- Сотрудники
- Посещаемость

### Этап 4 (FROZEN)
- Audit Log с privacy-safe структурированными details
- Объявления с публикацией для всего сада или группы и archive-only lifecycle
- Операционный Dashboard с garden-local датой и агрегацией по активным группам
- Стабилизация и финальная приёмка Stage 4

## Документы

- `AGENTS.md` и `docs/CURRENT_STATE.md` — первые источники для любой новой задачи.
- `docs/00-development-guide.md` — общая инструкция команды; Stage 1 bootstrap sections являются historical reference.
- `docs/01-stage-1-backend.md` — подробное ТЗ первого этапа для Backend-разработчика.
- `docs/02-stage-1-frontend.md` — подробное ТЗ первого этапа для Frontend-разработчика.
- `docs/03-api-contract-v0.1.md` — общий контракт первого этапа.
- `docs/04-mvp-roadmap.md` — примерное ТЗ последующих этапов.
- `docs/05-personal-data-baseline.md` — обязательные правила по персональным данным.
- `docs/06-product-scope.md` — зафиксированные границы продукта и ролей.
- `docs/07-project-master-draft.md` — полная черновая память проекта: история идеи, решения и технический контекст.
- `docs/08-team-access-and-environments.md` — смена ролей разработчиков, доступы, локальные окружения и правила хранения секретов.
- `docs/09-code-and-error-standards.md` — обязательные комментарии, обработка ошибок, logging и проверки перед PR.
- `docs/10-pre-development-audit.md` — контрольная проверка синхронизации перед Stage 1.
- `docs/12-stage-2-data-model-and-decisions.md` — решения по данным и границам Stage 2.
- `docs/13-stage-2-backend.md` и `docs/14-stage-2-frontend.md` — задания Stage 2.
- `docs/15-api-contract-stage-2.md` — API Stage 2.
- `docs/16-stage-2-acceptance.md` — проверенный сквозной сценарий и границы приёмки.
- `docs/17-stage-3-data-model-and-decisions.md` — решения по сотрудникам, посещаемости и ПДн.
- `docs/18-stage-3-backend.md` и `docs/19-stage-3-frontend.md` — задания Stage 3.
- `docs/20-api-contract-stage-3.md` — общий API Contract Stage 3.
- `docs/21-stage-3-delivery-plan.md` — порядок вертикальных срезов и проверок.
- `docs/22-stage-4-data-model-and-decisions.md` — frozen решения по данным и границам Stage 4.
- `docs/23-stage-4-backend.md` и `docs/24-stage-4-frontend.md` — frozen задания Stage 4.
- `docs/25-api-contract-stage-4.md` — frozen API Contract Stage 4.
- `docs/26-stage-4-acceptance.md` — финальная приёмка и freeze Stage 4.
- `CONTRIBUTING.md` — короткие правила ежедневной разработки и PR.

## Единая архитектура

```text
Browser
   ↓
Frontend — Next.js / React / TypeScript
   ↓ HTTP JSON /api/v1
Backend — FastAPI / Python
   ↓ SQLAlchemy
PostgreSQL
```

Frontend не создаёт и не использует собственную БД. SQLite, Firebase, Supabase и другие альтернативные хранилища не используются вместо PostgreSQL в MVP без отдельного согласования.

## Правило разработки

Новый этап не начинается массово, пока не выполнены критерии готовности предыдущего этапа. Каждая Issue выполняется в отдельной ветке и попадает в `main` через Pull Request.

Реальные персональные данные детей, родителей и сотрудников запрещено использовать в dev/test средах.


## Статус готовности

Stage 1–4 доступны в общей preview версии: Frontend Next.js работает с FastAPI и PostgreSQL без mock бизнес-данных. Помимо авторизации, групп, детей, представителей, сотрудников и посещаемости реализованы Audit, Announcements и Dashboard. Проверка основных браузерных сценариев описана в [PREVIEW.md](PREVIEW.md). Dev/test/preview используют только синтетические данные. Production/pilot требует отдельного legal/privacy/retention/infrastructure review; технический freeze не является заявлением о юридическом соответствии.
