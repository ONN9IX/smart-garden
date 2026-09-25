# Stage 1 — итоговая проверка и закрытие

**Статус:** завершение через PR #31.  
**Область:** Foundation + Auth для DIRECTOR/ADMIN.  
**Данные:** только синтетические.

## Что вошло

- Frontend: Next.js + React + TypeScript, Login, обязательная смена временного пароля, protected routes, AppShell, role-aware foundation, технический Dashboard, logout, responsive states.
- Backend: FastAPI + PostgreSQL, Organization, User, AuthSession, Alembic, Argon2id, server-side sessions, RBAC, tenant isolation, seed, OpenAPI и README.
- Интеграция: Frontend → Backend `/api/v1` → PostgreSQL без второй БД и без mocks в финальном E2E.

## Security baseline

- cookie `smart_garden_session` — HttpOnly, SameSite=Lax; production Secure;
- raw session token не возвращается JSON и не хранится в PostgreSQL;
- в PostgreSQL хранится только hash session token;
- пароль хранится только как Argon2id hash;
- смена временного пароля отзывает старые sessions;
- blocked user/organization проверяются Backend;
- tenant определяется из authenticated context;
- клиентский `organization_id` не является источником tenant context;
- validation errors нормализуются в HTTP 400 + `VALIDATION_ERROR`;
- dev/test используют только synthetic data.

## Автоматические проверки

На итоговой Stage 1 ветке CI выполняет:

1. Backend quality: Ruff, pytest, Alembic round-trip.
2. Frontend quality: ESLint, production build.
3. Browser auth flow: Playwright на реальной связке Next.js → FastAPI → PostgreSQL.
4. Local browser preview: Docker Compose поднимает PostgreSQL, Backend и Frontend.
5. Required status contexts `Backend checks` и `Frontend checks` являются финальными gate и появляются только после успешного прохождения всех четырёх блоков выше.

Последняя подтверждённая до финального closeout проверка: 14 Backend tests + 2 Playwright browser scenarios, все jobs green.

## Не входит в Stage 1

Группы, дети, родители/опекуны, сотрудники, посещаемость, объявления, платежи, СКУД, фото, AI и production deployment.

## Перед Stage 2

- начинать работу только от свежего `main`;
- сначала сформировать детальное ТЗ и API contract Stage 2;
- отдельно определить минимальные ПДн и доступы для Child/Guardian/Parent;
- реальные данные до production/legal readiness не использовать.

## Неблокирующий технический долг

CI может показывать предупреждения о lifecycle отдельных toolchain dependencies/actions. Они не ломают Stage 1 и должны обновляться отдельной maintenance-задачей с повторным CI, а не вместе с продуктовой логикой.
