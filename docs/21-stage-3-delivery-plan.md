# Stage 3 — порядок разработки и контроль

**Источники истины:** `docs/17-stage-3-data-model-and-decisions.md`, `docs/18-stage-3-backend.md`, `docs/19-stage-3-frontend.md`, `docs/20-api-contract-stage-3.md`. При конфликте с ранним `docs/04-mvp-roadmap.md` действует уточнённое решение Stage 3.

1. Foundation: миграции 0007/0008, Employee/Attendance models, schemas/types, auth/RBAC неизменны. Проверить upgrade/downgrade и ограничения на disposable PostgreSQL.
2. Employee vertical slice: Backend CRUD и архив, затем Frontend список/создание/detail/edit/archive. Два tenant, DIRECTOR/ADMIN/PARENT.
3. Employee account slice: Backend ADMIN account create/reset/block/unblock и отзыв сессий; затем одноразовый UI для DIRECTOR. Особый тест: ADMIN не архивирует Employee со связанным User.
4. Attendance vertical slice: Backend day view, computed unknown, upsert/PATCH и снимок группы; затем Frontend фильтры и ручные отметки.
5. Hardening: idempotent synthetic seed, OpenAPI/error contract, transaction rollback, privacy logging, responsive и browser E2E на полном стеке.
6. Integration: Stage 1/2/3 regression, migration round trip, Docker preview, required CI checks. Merge только после зелёных gates.

Каждая задача: одна Issue → отдельная ветка от свежего `main` → tests → Pull Request → CI → merge. Backend/Frontend могут выполнять разные разработчики, но API contract обновляется до кода при изменении решения.

## Риски, которые нельзя пропускать

- Выдача ADMIN доступа через карточку Employee должна быть только DIRECTOR; роль TEACHER ещё не существует.
- Архив карточки со связанным User — действие над доступом, поэтому ADMIN его не выполняет.
- Attendance group snapshot нельзя заменять текущим group_id ребёнка после перевода.
- `unknown` без записи — вычисленная строка, не массовая вставка при открытии дня.
- Отсутствие свободного comment защищает от случайной записи чувствительных сведений.
- Тестовый preview не является средой реальной обработки ПДн.
