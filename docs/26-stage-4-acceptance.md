# Stage 4 Acceptance

## 1. Acceptance result

**Stage 4: ACCEPTED**

На acceptance baseline `74712c293b83d1470d7f4445e9f6f299216e1ee2` обязательные технические критерии Stage 4 выполнены. Открытые BLOCKER и CURRENT STAGE findings отсутствуют. Статус `FROZEN` наступает после review, green required CI и merge acceptance PR по Issue #98.

## 2. Method and scope

Приёмка выполнена risk-based / diff-first по Stage 4 contracts, implementation diffs Issue #94 / PR #96 и Issue #95 / PR #97, relevant tests и required CI. После corrective Issue #99 / PR #100 повторно проверены только исправленная Attendance Audit test semantics, corrective diff и post-merge CI; неизменённый production scope не пересматривался с нуля.

Приняты вертикальные срезы:

- immutable tenant-scoped Audit для утверждённых Stage 2–4 mutations;
- Announcements для всего сада или одной активной группы;
- operational Dashboard для DIRECTOR/ADMIN на garden-local today.

Интеграционный путь: Browser → Next.js → `/api/v1` → FastAPI → SQLAlchemy → PostgreSQL.

## 3. Sources of truth

- `AGENTS.md` и `docs/CURRENT_STATE.md`;
- `docs/22-stage-4-data-model-and-decisions.md`;
- `docs/23-stage-4-backend.md`;
- `docs/24-stage-4-frontend.md`;
- `docs/25-api-contract-stage-4.md`;
- Issue #94 / PR #96;
- Issue #95 / PR #97;
- corrective Issue #99 / PR #100;
- Issue #98 и фактическая реализация на acceptance baseline.

## 4. Database and migrations

Migration chain непрерывна через `0010_audit_events → 0011_announcements`.

- `0010` создаёт append-only AuditEvent storage с tenant, actor, action/entity, privacy-minimized JSONB details, timestamp и утверждёнными tenant/query indexes.
- `0011` создаёт Announcements с tenant/user/group FK, target/status/non-empty checks и tenant/status/group indexes.
- `all` требует `group_id IS NULL`; `group` требует `group_id IS NOT NULL`.
- Downgrade каждой migration удаляет только собственные Stage 4 objects; migration round-trip сохраняет согласованную цепочку.
- Dashboard не добавляет таблицу.
- Незапланированных schema или public API изменений frozen Stage 1–3 не обнаружено.

PostgreSQL migration/constraint tests и required Alembic round-trip проходят. SQLite или вторая database architecture не используются.

## 5. Audit result

AuditEvent остаётся append-only на application/API boundary: публичных POST/PATCH/DELETE endpoints нет. Чтение списка и detail доступно только DIRECTOR; ADMIN/PARENT получают 403, foreign/missing event — 404. Все reads tenant-scoped и не возвращают `organization_id`.

Единый internal writer принимает только утверждённые action/entity combinations и структурно whitelisted details. Audit write выполняется в той же SQLAlchemy transaction, что и business mutation; rollback tests подтверждают отсутствие partial mutation и orphan audit event.

Покрыты утверждённые Group, Child, Guardian, ChildGuardian, Employee, PARENT/ADMIN account, Attendance и Announcement mutations. Audit details не содержат request bodies, passwords, hashes, temporary passwords, session tokens, auth secrets, announcement title/body, имена, phone/email/birth date, medical data или arbitrary notes.

Audit list сохраняет frozen sort contract `created_at DESC, id DESC`. Frontend `/audit` read-only, не разрешает edit/delete и не резолвит technical entity UUID в business-person names.

## 6. Corrective finding #99

Первый acceptance pass выявил один CURRENT STAGE finding: `test_all_stage4_audit_actions_and_privacy` ошибочно считал первый Attendance event событием `attendance.update`. При одинаковом transaction-stable `created_at` законная secondary sorting по случайному UUID могла поставить `attendance.create` первым.

Issue #99 / PR #100 исправили только `backend/tests/test_stage4_audit.py`:

- события выбираются по `action`, а не позиции;
- `attendance.create` отдельно проверяет privacy-safe `after`;
- `attendance.update` отдельно проверяет `before`, `after`, `changed_fields` и разрешённую структуру Attendance state;
- полный набор Audit actions и существующие privacy assertions сохранены.

Production API ordering, AuditEvent schema, timestamps, UUID generation, writer, transactions, Attendance logic, migrations, auth, RBAC и tenant behavior не изменялись. Targeted test прошёл отдельно и 10/10 повторов; полный backend suite и PR/post-merge required CI green. Finding закрыт, новых production findings corrective diff не создал.

## 7. Announcements result

DIRECTOR/ADMIN могут list/create/read/update/archive own-tenant announcements; PARENT получает 403. Tenant и actor берутся только из authenticated User, client-controlled `organization_id`, `created_by`, `updated_by` и `status` отклоняются.

- Публикация создаётся сразу `active`.
- `all` сохраняет `group_id = null`; `group` требует active same-tenant Group.
- Foreign Announcement или Group возвращают 404 без раскрытия tenant existence.
- Archive idempotent, hard delete/restore/draft отсутствуют.
- Archived announcement read-only и отклоняет PATCH с `ANNOUNCEMENT_ARCHIVED`.
- Title/body trim и limits `1–120` / `1–2000` применяются Backend и отражены в UI.
- Create/update/archive пишут Audit events без title/body; повторный idempotent archive не создаёт лишнее событие.

Attachments, rich HTML, push, email и SMS не добавлены.

## 8. Dashboard result

`GET /api/v1/dashboard/summary` доступен DIRECTOR/ADMIN и запрещён PARENT. Endpoint не принимает tenant или date: today вычисляется строго из `Organization.timezone` authenticated tenant.

- Учитываются только active children в active groups.
- Missing Attendance и explicit `unknown` считаются `unknown`.
- Группировка использует текущую active Child group; исторический Attendance group snapshot не меняется.
- Totals равны сумме group rows.
- Active groups/employees tenant-scoped.
- Реализация использует фиксированное число aggregate queries без N+1.
- Dashboard read не создаёт Audit events и не добавляет trends/history.

Timezone boundary, counters, transfer/current-group, archive exclusion, tenant isolation, totals, query count и RBAC покрыты tests.

## 9. API, tenant, RBAC and auth

- Base `/api/v1`, JSON `snake_case`, UUID и frozen 400/401/403/404/409 semantics сохранены.
- Ни один Stage 4 endpoint не принимает `organization_id`; tenant всегда выводится из authenticated User.
- Foreign Announcement/Audit UUID и foreign Group target следуют frozen 404 semantics.
- DIRECTOR: Dashboard, Announcement manage, Audit read.
- ADMIN: Dashboard и Announcement manage, без Audit read.
- PARENT: без Stage 4 management UI/API.
- UI hiding не заменяет Backend authorization.

Stage 4 не меняет auth/session architecture: server-side sessions, HttpOnly cookie, Argon2id, temporary-password change и server-side revocation остаются действующими. Raw tokens, hashes и credentials не входят в Stage 4 API/audit/logging.

## 10. Frontend and browser result

Role-aware navigation и routes `/dashboard`, `/announcements`, `/announcements/new`, `/announcements/[id]`, `/audit` соответствуют RBAC. Dashboard/Announcements имеют loading, empty, error и retry states. Announcement archive требует confirmation; archived state read-only.

Announcement title/body остаются только в component/request memory: не помещаются в URL, query parameters, browser storage или console. Filters используют только enums/UUID. Audit rows также не сохраняются в browser storage. Privacy notice предупреждает не вводить passwords, medical data и unnecessary/sensitive personal data.

Real Playwright flow проверяет DIRECTOR/ADMIN/PARENT permissions, Dashboard totals, whole-garden/group announcement create, edit/archive/read-only, cross-tenant 404, representative Audit events и отсутствие business-person names, secrets и announcement free text в Audit UI. Desktop/tablet/mobile overflow и runtime errors также проверены.

## 11. Personal data and 152-FZ technical review

Audit actor activity является processing of personal data, поэтому Audit read ограничен DIRECTOR, а details минимизированы whitelist. Dashboard не вводит новые PII fields. Announcement title/body — единственный новый intentional free-text risk; purpose ограничен operational announcements, UI содержит privacy warning, attachments отсутствуют.

Business free text и secrets не записываются в Audit/logs, URLs или browser storage. Tenant isolation/RBAC применяются независимо на Backend. Dev/test/preview используют только synthetic data.

Эта техническая приёмка не подтверждает полное юридическое соответствие 152-ФЗ. До реального pilot/production необходимы отдельные актуальные legal, privacy, retention и infrastructure reviews и организационные меры.

## 12. Regression and CI evidence

- PR #96 Audit delivery, run `36389154301`: 6/6 required jobs green.
- PR #97 Operations delivery, run `36392669270`: 6/6 required jobs green.
- PR #100 corrective, run `36396001441`: 6/6 required jobs green.
- Post-merge `main` baseline `74712c293b83d1470d7f4445e9f6f299216e1ee2`, run `36424886944`: Backend quality/checks, Frontend quality/checks, real Browser integration and Docker preview — 6/6 green.

Required CI covers Ruff, complete PostgreSQL pytest, Alembic round-trip, frontend lint/build, real Browser → Next.js → FastAPI → PostgreSQL integration, Docker preview and required gates. Acceptance PR must also remain green before merge.

## 13. Findings by severity

- **BLOCKER:** none.
- **CURRENT STAGE:** none open; the Attendance Audit test finding is closed by Issue #99 / PR #100.
- **TECH DEBT:** Issue #32, supported ESLint/GitHub Actions toolchain maintenance before production/pilot hardening; does not block Stage 4 freeze.
- **FUTURE:** pilot/production legal, privacy, retention and infrastructure review; TEACHER, full PARENT UI, push/email/SMS, attachments, trends/history and external integrations.

## 14. Freeze boundary

After review, green required CI and merge of the Issue #98 acceptance PR, Stage 1–4 are FROZEN. Later Stage 4 changes require a bug/security/privacy/regression reason or explicit architecture decision. Stage 5 is not started by this acceptance.
