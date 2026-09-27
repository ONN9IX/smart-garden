# Stage 3 Acceptance

## 1. Acceptance result

**Stage 3: ACCEPTED**

На `main` commit `2899cb8c3c8dced1f6c802d57aa5927b0065a522` обязательные критерии Stage 3 выполнены. BLOCKER и CURRENT STAGE findings отсутствуют. Статус `FROZEN` наступает только после review, green required CI и merge acceptance PR по Issue #86.

## 2. Scope

Приняты вертикальные срезы:

- карточки Employee и управление связанным ADMIN account;
- ручная Attendance с вычисляемым `unknown`, отметками `present`/`absent`, фильтрами и историческим снимком группы;
- `Organization.timezone` как tenant-level настройка, необходимая для календарной даты сада.

Стек интеграции: Browser → Next.js → `/api/v1` → FastAPI → SQLAlchemy → PostgreSQL.

## 3. Sources of truth

- `docs/17-stage-3-data-model-and-decisions.md`;
- `docs/18-stage-3-backend.md`;
- `docs/19-stage-3-frontend.md`;
- `docs/20-api-contract-stage-3.md`;
- Issue #86 и фактическая Stage 3 implementation/test реализация в `main`;
- QA3-02: Issue #84 / PR #85;
- QA3-03: Issue #87 / PR #89;
- STAGE3-DATE: Issue #88 / PR #90.

## 4. Database result

Migration chain непрерывна: `0007 employees → 0008 attendance → 0009 organization timezone`.

- `0007` создаёт tenant-scoped Employee, optional unique Employee↔User link, status/non-empty checks и индекс organization/status.
- `0008` создаёт Attendance с UUID FK, unique `(child_id, date)`, status/time checks, tenant/date indexes и сохранённым `group_id` как историческим снимком.
- `0009` безопасно добавляет `organizations.timezone String(64)`, backfill `Europe/Moscow`, затем `NOT NULL` и DB default; downgrade удаляет только timezone.
- ORM соответствует migrations. Attendance остаётся PostgreSQL `DATE` и local wall `TIME` без преобразования в UTC datetime.
- PostgreSQL upgrade/downgrade/upgrade и constraint tests проходят. SQLite и вторая БД не используются.
- Незапланированных изменений предыдущих Stage schema в corrective PR #89/#90 нет.

## 5. Backend result

Employee list/create/detail/patch/archive/restore реализованы с tenant filtering и безопасными ошибками. Archive связанного Employee блокирует ADMIN и отзывает его sessions; restore карточки не разблокирует User.

Account lifecycle доступен только DIRECTOR: create, one-time temporary password, reset, block и unblock. Username генерируется случайно, пароль хранится как Argon2id hash, новый account получает `must_change_password`, reset/block/archive отзывают sessions. Повторный account и privilege escalation отклоняются.

Attendance поддерживает day view, computed и explicit `unknown`, `present`, `absent`, atomic upsert, PATCH, created/updated actor UUID, group snapshot, историю после перевода Child, archived Child/Group rules и проверки local wall time. Future-date validation для GET day и POST/upsert использует календарную дату Organization аутентифицированного tenant.

## 6. Frontend result

Employees UI покрывает list/create/edit/detail, active/archived/all, archive/restore и role-aware account controls. Формы сохраняют введённые значения при safe save error и допускают retry.

Archive и restore требуют confirmation. Cancel restore не отправляет API request. Restore confirmation явно сообщает, что восстановление Employee не разблокирует связанного User автоматически.

One-time username/password берутся непосредственно из POST create/reset, существуют только в component memory и исчезают после close, navigation или refresh. Последующий GET Employee не используется для восстановления temporary password; browser storage, URL и console для credentials не применяются.

Attendance UI сбрасывает состояние предыдущей даты, игнорирует stale response, синхронизирует child selector с текущими group/status results и сохраняет исторический group snapshot из Backend. Desktop/tablet/mobile overflow и browser runtime errors проверяются E2E.

## 7. API Contract result

- Base path `/api/v1`, JSON `snake_case`, UUID и утверждённые 400/401/403/404/409 semantics сохранены.
- Tenant и actor определяются server-side по authenticated User; `organization_id` и timezone не принимаются от клиента.
- Employee GET не возвращает password/hash/session token или temporary password.
- Attendance request/response shape не изменён: date — `YYYY-MM-DD`, times — local `HH:MM`; timezone в payload отсутствует.
- Новых недокументированных Stage 3 endpoints или transport fields не обнаружено.

## 8. Tenant isolation result

Backend tests и real E2E используют два synthetic tenant. Tenant A получает 404 и не может читать/изменять Employee, Child, Group или Attendance Tenant B, а также создать Attendance для чужого Child. Timezone выбирается только по Organization текущего authenticated User; cross-tenant timezone lookup отсутствует.

## 9. RBAC result

- DIRECTOR выполняет утверждённые Employee, account и Attendance management actions.
- ADMIN работает с разрешёнными Employee/Attendance operations, но не видит account controls и получает 403 от account lifecycle API.
- PARENT не видит Stage 3 management navigation; direct URLs redirect в parent area, Backend Employee/Attendance API возвращает 403.

UI hiding не используется как замена Backend authorization.

## 10. Auth and security result

Сохраняются server-side sessions, HttpOnly cookie и Argon2id. Raw session token и password hash отсутствуют в API JSON. Temporary password возвращается только один раз в POST create/reset.

Reset, block и archive связанного Employee отзывают действующие sessions. Старые temporary/current credentials после reset не работают. Restore Employee сохраняет User blocked до отдельного DIRECTOR unblock.

## 11. Organization timezone and calendar date

`Organization.timezone` валидируется через stdlib `ZoneInfo`; invalid IANA value завершается явной ошибкой без silent UTC fallback. Python и DB default для новых Organization — `Europe/Moscow`, существующие synthetic Organization получают это значение migration/seed.

Единый helper вычисляет `datetime.now(ZoneInfo(actor.organization.timezone)).date()`. Browser timezone, server local timezone, UTC calendar date, fixed offset и request timezone не используются.

Boundary tests подтверждают:

- `Europe/Moscow` уже находится в следующей календарной дате относительно UTC;
- следующий garden-local day отклоняется как `INVALID_ATTENDANCE_DATE`;
- `America/Los_Angeles` ещё находится в предыдущей дате при том же UTC instant;
- GET list_day и POST/upsert используют одинаковое правило;
- два tenant при одном instant могут иметь разный today;
- invalid timezone fail-closed.

## 12. Personal data result

Corrective изменения не расширили категории ПДн.

- Employee: first name, last name, optional middle name, position и технические IDs/timestamps.
- Attendance: Child UUID, date, status, local arrival/departure, group snapshot, actor UUID и технические timestamps.
- Не добавлены Employee phone/email/address/birth date/salary/passport, medical/diagnosis/reason/comment/photo, arbitrary notes или документы.
- `Organization.timezone` не является ПДн и не требует address, city, region или coordinates.
- Dev/test/preview используют только synthetic data. Credentials не сохраняются в browser storage, URL или console; intentional request-body/temporary-password logging отсутствует.

Перед реальным production/pilot deployment необходимо отдельное актуальное правовое и инфраструктурное review по 152-ФЗ и связанным требованиям.

## 13. Integration and regression result

Real Playwright flow проходит через Browser → Next.js → FastAPI → PostgreSQL и покрывает Employee create/edit, ADMIN create/login/forced password change, account denial для ADMIN, reset/revocation/block, archive/restore confirmation и отсутствие auto-unblock.

Тот же flow покрывает computed unknown, present→absent, group/status/child filters, date reset, historical group snapshot, PARENT UI/direct URL/API denial, два tenant, desktop/tablet/mobile overflow и отсутствие runtime errors. Mocked QA3-02/QA3-03 tests остаются только адресными regressions и не заменяют real E2E.

Stage 1/2 browser regressions сохранены в общем Playwright suite.

## 14. CI evidence

- CI run #76 для PR #85: Backend quality, Frontend quality, real browser integration, Docker preview и required gates — success.
- CI run #81 для PR #89: те же обязательные jobs — success; полный browser suite — 8/8 passed.
- CI run #83 для PR #90: Backend quality — success (`51 passed`), PostgreSQL/Alembic round-trip — success, Frontend lint/build — success, real browser integration — success (`8 passed`), Docker preview и required gates — success.
- Acceptance PR по Issue #86 обязан получить собственный green required CI до merge.

## 15. Corrective acceptance findings

Первоначальная проверка Issue #86 выявила два CURRENT STAGE findings:

1. Issue #87 / PR #89 исправили restore confirmation и расширили real Stage 3 browser coverage.
2. Issue #88 / PR #90 заменили UTC calendar date на tenant-aware `Organization.timezone` и добавили timezone boundary/migration tests.

Targeted re-check подтверждает устранение обоих findings. Новых BLOCKER или CURRENT STAGE findings нет.

## 16. Known limitations and out of scope

Не входят в Stage 3: TEACHER, СКУД, turnstiles, tablets, biometric/face recognition, automatic attendance, cameras, medical/reason/comment fields, billing/payroll, notifications/chat и Stage 4 modules.

Stage 3 acceptance не означает production legal/privacy readiness и не разрешает ввод реальных ПДн до отдельного pilot/production review.
