# Проверить текущий Smart Garden MVP в браузере

Preview использует только синтетические данные. Реальные персональные данные в dev/test/preview запрещены.

## 1. Запуск

Нужны Docker Desktop, Docker Compose и Git Bash.

```bash
git fetch origin
git switch main
git pull --ff-only
bash scripts/start-preview.sh
```

`PLATFORM_ENCRYPTION_KEY` для владельца хранится отдельно от репозитория в
`%LOCALAPPDATA%\SmartGarden\platform-owner\platform-owner.env`. На Windows
Git Bash скрипты используют тот же каталог автоматически. Ключ при запуске не
создаётся и не меняется. Если файл отсутствует, preview поднимется для
диагностики, а platform auth останется fail-closed.

### Постоянный локальный доступ PLATFORM_OWNER

До первой настройки ограничьте доступ к внешнему каталогу текущей учётной
записью Windows и SYSTEM. Выполните в PowerShell:

```powershell
$ownerDir = Join-Path $env:LOCALAPPDATA 'SmartGarden\platform-owner'
New-Item -ItemType Directory -Force $ownerDir | Out-Null
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
icacls $ownerDir /inheritance:r /grant:r "*$sid`:(OI)(CI)F" 'SYSTEM:(OI)(CI)F'
```

Запустите preview, затем выполните read-only диагностику:

```bash
bash scripts/start-preview.sh
bash scripts/setup-platform-owner-local.sh diagnose
```

Диагностика показывает состояние preview/volume, HTTP-доступность
`/platform/login`, число операторов, их username/status/MFA-present и только
статус ключа; для существующего MFA также проверяет расшифровку ciphertext, не
показывая результат. Она не читает и не печатает хеши паролей, MFA-секрет,
ключ, URI или содержимое env-файлов.

Если оператор уже существует, используйте именно его username и текущий ключ.
Не запускайте `init-key` или `create`; при штатной настройке повторите запуск
preview и войдите через `http://localhost:3000/platform/login`, пароль и TOTP
вводятся владельцем.

`init-key` разрешён только после диагностики пустой таблицы platform operators.
Он создаёт ключ один раз во внешнем env-файле; стартовый скрипт никогда не
перегенерирует его:

```bash
bash scripts/setup-platform-owner-local.sh init-key
bash scripts/start-preview.sh
bash scripts/setup-platform-owner-local.sh create platform-owner-local
```

Команда `create` откажется работать, если оператор уже существует. Она
использует доверенный offline bootstrap, запросит пароль без отображения и
создаст enrollment URI во внешнем `platform-owner-enrollment.json`. Откройте
его только на этом компьютере, добавьте аккаунт в authenticator и безопасно
удалите файл после enrollment. URI является секретом MFA.

Если исходный ключ потерян, не запускайте `init-key`: он откажет при наличии
оператора. Только для подтверждённого key-loss предусмотрено явное действие:

```bash
bash scripts/setup-platform-owner-local.sh recover platform-owner-local
```

Recovery запросит точное подтверждение `LOST-KEY-RECOVERY <username>`, затем
существующий bootstrap попросит новый пароль и точное повторное подтверждение
username. Recovery заменяет MFA-секрет, отзывает platform-сессии и пишет audit;
старый TOTP перестанет работать. При нескольких операторах команда остановится,
ничего не удаляя. При сохранном ключе recovery также меняет MFA и требует
явного запуска владельцем.

Внешний env-файл нужен для стабильности после перезапуска Windows и обычного
`docker compose down`/up. Для этого локального preview Compose передаёт ключ в
переменную окружения backend. Поэтому пользователь с доступом к Docker daemon
может увидеть его через `docker inspect` или `docker compose config`; не запускайте
эти команды с выводом на общий экран и не сохраняйте их результат. Доступ к
Docker daemon означает доверие к владельцу машины. Этот локальный механизм не
является production-secure.

Откройте:

- Frontend: http://localhost:3000/login
- API health: http://localhost:8000/api/v1/health
- OpenAPI: http://localhost:8000/docs

Временные пароли выводятся в терминале только при создании соответствующего synthetic аккаунта. Они не сохраняются в открытом виде и не коммитятся.

Если нужный PARENT/TEACHER аккаунт уже существует, но пароль неизвестен, используйте существующий DIRECTOR flow управления аккаунтом и безопасно получите новый одноразовый временный пароль. Не добавляйте статические demo-пароли в репозиторий.

## 2. Текущий продуктовый baseline

Активны:

- Dashboard;
- Children;
- Groups;
- Guardians / Parents;
- Employees;
- Teachers / assignments;
- Attendance;
- Schedule;
- Announcements;
- Tasks;
- Communications;
- Notifications;
- Audit;
- Organization Settings;
- Auth/account management.

OFF, но сохранены в коде и данных:

- Polls;
- Incidents;
- Diary;
- Photos;
- Photo consents;
- Document notices.

Также пока не реализуем runtime для Contracts/Billing, Entry Kiosk, psychology/development-support и SaaS tenant subscription.

## 3. Рекомендуемый сценарий демонстрации

### DIRECTOR

1. Войти под synthetic DIRECTOR.
2. Открыть Dashboard и показать garden-local текущую дату.
3. Открыть Groups.
4. Открыть Children и карточку synthetic ребёнка.
5. Открыть Guardians и связь родителя с ребёнком.
6. Открыть Employees / Teachers и показать назначение воспитателя.
7. Открыть Attendance.
8. Открыть Schedule.
9. Создать или показать synthetic Announcement.
10. Создать или показать Task воспитателю.
11. Открыть Group communications.
12. Показать Audit.
13. Показать Settings.

OFF-модули не должны отображаться в меню или карточке ребёнка.

### TEACHER

1. Войти под synthetic TEACHER.
2. Открыть Today.
3. Показать назначенную группу.
4. Открыть roster и доступные контакты родителей.
5. Открыть Attendance и отметить synthetic ребёнка.
6. Проверить, что дата по умолчанию соответствует garden-local дате сервера.
7. Открыть Schedule.
8. Открыть Communications.
9. Открыть Announcements.
10. Открыть Tasks / Notifications через раздел «Ещё».

Воспитатель видит только назначенные ему группы.

### PARENT

1. Убедиться, что synthetic Guardian связан с synthetic Child и имеет PARENT account.
2. Войти под PARENT.
3. На вкладке «Сегодня» показать:
   - своего ребёнка;
   - текущую группу;
   - сегодняшнюю посещаемость;
   - время прихода/ухода при наличии;
   - расписание группы на сегодня.
4. Открыть Announcements.
5. Открыть Messages.
6. Создать/открыть прямой диалог с воспитателем.

PARENT не должен видеть другого ребёнка или внутренние management/teacher экраны.

## 4. Сброс локальной preview-БД

Если нужны полностью новые synthetic аккаунты и данные:

```bash
docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml down -v
bash scripts/start-preview.sh
```

Команда удаляет только локальный preview volume.

**Не используйте `down -v`**, если нужно сохранить platform owner, пароль/MFA,
аудит или synthetic preview данные. Для штатного перезапуска используйте только
`down` без `-v`, затем `bash scripts/start-preview.sh`.

Чтобы просто остановить preview и сохранить данные:

```bash
docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml down
```

## 5. Граница preview

Preview не является production deployment instruction.

Техническая демонстрация не означает полную 152-ФЗ готовность и не разрешает использование реальных ПДн до отдельного legal/privacy/infrastructure review.
