# Стандарты кода, комментариев и обработки ошибок

**Кому читать:** любому разработчику перед первой задачей в новой для него части проекта.  
**Статус:** обязательный стандарт.  
**При конфликте:** API Contract и security requirements имеют приоритет.

# 1. Зачем этот документ

Разработчики меняются Frontend/Backend ролями. Код должен быть понятен следующему человеку без восстановления логики по переписке.

# 2. Комментарий в source-файле

Каждый вручную созданный **нетривиальный** source-файл получает короткий заголовочный комментарий.

Python:
```python
"""Auth service.

Purpose: создаёт и завершает пользовательские сессии.
Input: User + credentials из API слоя.
Output: session/result без раскрытия password/hash.
Security: tenant и user status проверяются на Backend.
"""
```

TypeScript:
```ts
/**
 * Auth API client.
 * Purpose: единственная точка HTTP-вызовов auth endpoints.
 * Source of truth: docs/03-api-contract-v0.1.md.
 * Security: credentials передаются только через HttpOnly cookie.
 */
```

Не нужны искусственные заголовки для:
- generated files;
- lock files;
- пустых `__init__.py`;
- простых barrel/index exports;
- auto-generated migrations (ручная часть migration всё равно должна быть понятна по имени).

# 3. Комментарии внутри кода

Писать комментарий, когда нужно объяснить:
- почему принято неочевидное решение;
- security/tenant restriction;
- формат внешнего контракта;
- временный workaround с обязательным TODO + Issue;
- сложную бизнес-логику.

Не писать комментарии вида:
```text
i += 1 // увеличиваем i на 1
```

# 4. TODO

Любой TODO должен ссылаться на Issue:
```text
TODO(#123): ...
```

Безномерные TODO не оставлять.

# 5. Backend errors

Backend обязан:
- нормализовать ожидаемые ошибки в общий API error contract;
- validation errors возвращать как HTTP 400 + `VALIDATION_ERROR`;
- 401 использовать для отсутствующей/недействительной session;
- 403 — для запрета/blocked state;
- 404 — для отсутствующего/скрытого tenant policy ресурса;
- 409 — для конфликтов;
- 500 — только для непредвиденной ошибки.

Клиенту нельзя отдавать:
- Python traceback;
- SQL error;
- connection string;
- внутренние exception messages;
- raw session token;
- password/hash.

# 6. Backend exception handling

- Не использовать широкий `except Exception: pass`.
- DB transaction при ошибке должна rollback.
- Не превращать любую ошибку в 200.
- Непредвиденная ошибка логируется технически без секретов/лишних ПДн и возвращается как `INTERNAL_ERROR`.
- Security failure должна быть fail-closed: при сомнении доступ не предоставлять.

# 7. Frontend errors

Frontend:
- работает через единый API client;
- не разбирает ошибки отдельно в каждом компоненте;
- показывает безопасный пользовательский текст;
- не выводит raw response/stack trace;
- network failure отличается от неверного пароля;
- не скрывает ошибку молча;
- не считает скрытую кнопку механизмом authorization.

# 8. Logging

Разрешено:
- request_id;
- method/path;
- status;
- duration;
- user_id;
- organization_id;
- безопасный error code.

Запрещено:
- password;
- password_hash;
- temporary password;
- raw session token/cookie;
- Authorization header;
- полный auth request body;
- лишние ПДн.

# 9. Naming

API transport:
- `snake_case`.

Python:
- стандартный snake_case / PascalCase classes.

TypeScript internal code:
- idiоматичный camelCase разрешён;
- transport types должны точно отражать API;
- преобразование имён, если оно вообще нужно, делается централизованно, а не в компонентах.

# 10. Проверки перед PR

Backend:
- `ruff check .`;
- `pytest`;
- migrations apply cleanly;
- secrets scan глазами через `git diff --cached`.

Frontend:
- `npm run lint`;
- `npm run build`;
- browser console без критических ошибок;
- Network requests идут только в утверждённый API.

# 11. Definition of understandable code

Следующий разработчик должен понять:
- где вход в модуль;
- какой контракт используется;
- где данные хранятся;
- какие ошибки возможны;
- какие security ограничения действуют;
- как локально проверить изменение.

Если для этого необходимо личное объяснение автора, документации недостаточно.
