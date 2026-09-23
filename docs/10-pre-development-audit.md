# Pre-development audit — Stage 1

**Дата:** 23 сентября 2026  
**Назначение:** контрольная точка перед началом кода Stage 1.

# Проверено

- [x] Один репозиторий для Frontend/Backend.
- [x] PostgreSQL — единственная application DB.
- [x] Local PostgreSQL воспроизводится через Docker Compose.
- [x] Frontend не имеет прямого DB access.
- [x] Стек Backend/Frontend зафиксирован.
- [x] Роли разработчиков могут меняться между этапами.
- [x] Environment не зависит от личного пароля разработчика.
- [x] API base path единый: `/api/v1`.
- [x] Auth transport зафиксирован через HttpOnly cookie.
- [x] Server-side session policy зафиксирована.
- [x] Validation policy единая: HTTP 400.
- [x] JSON transport naming: snake_case.
- [x] IDs Stage 1: UUID.
- [x] Tenant context определяется Backend.
- [x] Dev/test используют synthetic data.
- [x] `.gitignore` закрывает environment, venv, node_modules и build output.
- [x] `.editorconfig` фиксирует базовое форматирование.
- [x] Pull Request template содержит security/integration checklist.
- [x] Code/comment/error standard создан.
- [x] Master draft хранит историю решений.
- [x] Stage 1 имеет общую E2E Integration Issue.

# Блокирующие правила

До merge нельзя:
- вводить второй API contract;
- использовать SQLite/Firebase/Supabase как application DB;
- коммитить production/shared secret;
- использовать реальные ПДн;
- менять network fields только во Frontend или только в Backend;
- обходить RBAC/tenant checks;
- оставлять обязательную настройку только локально.

# Gate перед началом

Репозиторий технически готов к Stage 1.

Каждый разработчик перед кодом:
1. читает свою Issue;
2. читает `docs/00-development-guide.md`;
3. читает `docs/03-api-contract-v0.1.md`;
4. читает `docs/08-team-access-and-environments.md`;
5. читает `docs/09-code-and-error-standards.md`;
6. подтягивает свежий `main` в свою стартовую ветку.

# Gate после Stage 1

Stage 1 закрывается только через INTEGRATION-01:
`Frontend → Backend → PostgreSQL`, без mocks и второй БД.
