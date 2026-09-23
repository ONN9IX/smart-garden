# Доступы, окружения и смена ролей разработчиков

> Этот документ обязателен для команды. Его цель — сделать так, чтобы любой разработчик мог в любой момент перейти с Frontend на Backend или обратно без запроса чужих паролей, локальных файлов и ручной передачи секретов.

# 1. Роли разработчиков не постоянные

Frontend/Backend — это **роль на конкретный этап**, а не постоянная специализация человека.

Текущее распределение Stage 1:
- ONN9IX — Frontend;
- F1zname — Backend.

План для следующих этапов допускает смену:
- ONN9IX может перейти на Backend;
- F1zname может перейти на Frontend;
- дальнейшее распределение определяется перед началом каждого Stage.

Нельзя строить инфраструктуру так, чтобы Backend мог запустить только один конкретный человек.

# 2. Главное правило доступов

Ни один рабочий компонент не должен зависеть от:
- пароля, известного только одному разработчику;
- файла, который существует только на одном компьютере;
- личного аккаунта разработчика в инфраструктуре;
- устной передачи секретов в Telegram/чатах;
- ручной настройки, которая нигде не описана.

Любой разработчик с доступом к репозиторию должен иметь возможность поднять dev-среду по документации.

# 3. Что хранится в Git

Можно хранить:
- `.env.example`;
- dev-only Docker configuration;
- публичные локальные порты;
- названия dev database/user;
- команды запуска;
- миграции;
- seed scripts;
- synthetic demo data;
- документацию.

Нельзя хранить:
- production passwords;
- production database URLs;
- API keys;
- private tokens;
- real JWT/session secrets;
- private SSH keys;
- реальные персональные данные.

# 4. Локальная PostgreSQL

Для команды выбран воспроизводимый вариант через Docker Compose.

Файл:
- `docker-compose.yml`

Команда:
```bash
docker compose up -d postgres
```

Локальные параметры по умолчанию:
- host: `localhost`
- port: `5432`
- database: `smart_garden`
- user: `smart_garden`
- password: `smart_garden_local_only`

**Это не секрет и не production credential.** Это фиксированное значение исключительно для локального контейнера с синтетическими данными.

Порт PostgreSQL привязан только к `127.0.0.1`.

Production/staging никогда не должны использовать этот пароль.

# 5. Backend local environment

Backend `.env.example` должен содержать совместимый local DATABASE_URL:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://smart_garden:smart_garden_local_only@localhost:5432/smart_garden
SECRET_KEY=CHANGE_ME_LOCAL
AUTH_TOKEN_TTL=3600
CORS_ORIGINS=http://localhost:3000
```

Разработчик:
1. копирует `.env.example` → `.env`;
2. задаёт локальный `SECRET_KEY`;
3. запускает PostgreSQL через Docker;
4. применяет migrations;
5. запускает Backend.

Для локального SECRET_KEY не нужно спрашивать другого разработчика. Каждый создаёт свой локальный.

# 6. Frontend local environment

Frontend `.env.example`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Разработчик копирует его в `.env.local`.

Frontend не требует database password вообще.

# 7. Demo application users

Demo users создаются через seed, а не принадлежат конкретному разработчику.

План:
- `director-demo`
- `admin-demo`

Пароль не хранится в Git.

Seed/utility должен:
- либо сгенерировать temporary password и вывести его один раз локально;
- либо принять локальное значение из environment.

Таким образом новый Backend-разработчик может сам пересоздать demo environment и не просить пароль у предыдущего.

# 8. Staging и Production

Когда появятся общие удалённые окружения:

## Каждый человек
- использует свой GitHub account;
- получает только нужный уровень доступа;
- не использует общий GitHub login.

## Machine secrets
Хранятся не у человека, а в:
- GitHub Actions / GitHub Environment Secrets;
- либо отдельном командном secret manager.

К таким секретам относятся:
- DATABASE_URL;
- production SECRET_KEY;
- deployment tokens;
- third-party API keys.

Приложение/CI получает секрет во время запуска. Разработчику не обязательно знать его значение.

# 9. Никаких общих human passwords

Нельзя создавать:
- один общий GitHub аккаунт на двоих;
- один общий production admin login для разработчиков;
- один пароль от production БД, который пересылается в сообщениях.

Если разработчику нужен доступ к админке/стенду:
- создаётся отдельный account на его имя/технический username;
- действия можно отследить;
- доступ можно отозвать отдельно.

# 10. Переключение Frontend → Backend

Если ONN9IX на следующем Stage переходит на Backend:

1. обновляет `main`;
2. читает актуальный Backend README и Issue;
3. устанавливает Python/Docker, если их ещё нет;
4. выполняет `docker compose up -d postgres`;
5. копирует Backend `.env.example` → `.env`;
6. создаёт собственный local SECRET_KEY;
7. применяет migrations;
8. запускает seed;
9. запускает Backend;
10. выполняет тесты.

Никаких данных у F1zname запрашивать не требуется.

# 11. Переключение Backend → Frontend

Если F1zname переходит на Frontend:

1. обновляет `main`;
2. читает Frontend README и Issue;
3. устанавливает Node.js;
4. устанавливает dependencies;
5. копирует `.env.example` → `.env.local`;
6. запускает Frontend;
7. использует общий Backend API contract.

Никаких токенов/паролей от ONN9IX запрашивать не требуется.

# 12. Передача задачи между разработчиками

Каждая завершённая задача должна оставлять после себя:
- код в Git;
- migrations;
- `.env.example`;
- README;
- tests;
- понятный PR;
- актуальную Issue;
- при необходимости запись в master draft.

Фраза «у меня локально работает» недостаточна.

Правильный критерий:
**другой разработчик смог поднять это с чистого окружения по репозиторию.**

# 13. Handover checklist

Перед сменой разработчика:

- [ ] изменения merged в `main`;
- [ ] migrations committed;
- [ ] `.env.example` актуален;
- [ ] README актуален;
- [ ] команды запуска актуальны;
- [ ] seed работает;
- [ ] tests проходят;
- [ ] нет секретов в Git;
- [ ] нет обязательных файлов только на старом компьютере;
- [ ] Issue описывает следующий шаг;
- [ ] API contract актуален.

# 14. Что делать при появлении нового секрета

Новый секрет сначала классифицируется.

## Local dev-only
Если значение не даёт доступа ни к какому удалённому ресурсу и относится только к локальному synthetic environment, допускается стандартное dev-only значение.

## Shared staging/production
Не коммитить. Хранить централизованно в secret storage / GitHub Environment Secrets.

## Human account
У каждого человека свой account. Пароли между разработчиками не передаются.

# 15. Ключевой принцип

```text
Код + документация + migrations + seed + env template
                     ↓
             любой разработчик
                     ↓
        воспроизводимая dev-среда
```

У проекта не должно быть «пароля от Backend-разработчика», «его базы» или «его локальной версии». Backend, Frontend и БД принадлежат проекту, а не конкретному человеку.
