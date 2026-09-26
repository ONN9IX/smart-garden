/** Stage 3 acceptance path: Browser -> Next.js -> FastAPI -> PostgreSQL. */
import { expect, test, type APIResponse, type BrowserContext, type Page, type Request } from "@playwright/test";

const apiBase = "http://localhost:8000/api/v1";
test.setTimeout(180_000);

async function login(page: Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Логин").fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
}

async function rotate(page: Page, prefix: string, destination = /\/dashboard$/) {
  await expect(page).toHaveURL(/\/change-password$/);
  const password = `${prefix}-${crypto.randomUUID()}`;
  await page.getByLabel("Новый пароль", { exact: true }).fill(password);
  await page.getByLabel("Повторите новый пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
  await expect(page).toHaveURL(destination);
  return password;
}

function watchRuntimeErrors(page: Page, errors: string[]) {
  page.on("pageerror", (error) => errors.push(error.message));
}

async function expectNoHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

async function expectSuccess(response: APIResponse) {
  if (response.status() >= 300) throw new Error(`Unexpected API ${response.status()}: ${await response.text()}`);
  return response;
}

async function loginApi(context: BrowserContext, username: string, password: string) {
  return context.request.post(`${apiBase}/auth/login`, { data: { username, password } });
}

test("complete Stage 3 real browser acceptance", async ({ page, browser }) => {
  const directorTemporary = process.env.CI_STAGE3_DIRECTOR_PASSWORD;
  const otherDirectorTemporary = process.env.CI_STAGE3_OTHER_DIRECTOR_PASSWORD;
  if (!directorTemporary) throw new Error("CI_STAGE3_DIRECTOR_PASSWORD is required");
  if (!otherDirectorTemporary) throw new Error("CI_STAGE3_OTHER_DIRECTOR_PASSWORD is required");

  const errors: string[] = [];
  const suffix = crypto.randomUUID().slice(0, 8);
  const employeeLastName = `Сотрудник${suffix}`;
  const groupAName = `Группа А ${suffix}`;
  const groupBName = `Группа Б ${suffix}`;
  const childFirstName = `Ребёнок${suffix}`;
  const attendanceDay = "2025-10-10";
  const nextDay = "2025-10-11";
  watchRuntimeErrors(page, errors);

  // DIRECTOR: create and edit an Employee, then issue one-time ADMIN credentials.
  await login(page, "stage3-director-demo", directorTemporary);
  await rotate(page, "director-stage3");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/employees/new");
  await expectNoHorizontalOverflow(page);
  await page.getByLabel("Фамилия").fill(employeeLastName);
  await page.getByLabel("Имя").fill("Тестовый");
  await page.getByLabel("Должность").fill("Администратор");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page).toHaveURL(/\/employees\/[a-f0-9-]+$/);
  const employeeUrl = page.url();
  const employeeId = employeeUrl.split("/").pop()!;
  await page.getByRole("button", { name: "Изменить" }).click();
  await page.getByLabel("Должность").fill("Старший администратор");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.getByText("Старший администратор", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Выдать доступ администратора" }).click();
  const credentials = page.getByRole("region", { name: "Одноразовые реквизиты" });
  await expect(credentials).toBeVisible();
  const adminUsername = await credentials.getByText("Логин:").locator("strong").innerText();
  const adminTemporary = await credentials.getByText("Временный пароль:").locator("strong").innerText();
  await page.setViewportSize({ width: 390, height: 844 });
  await expectNoHorizontalOverflow(page);
  await page.getByRole("button", { name: "Закрыть и скрыть пароль" }).click();
  await page.reload();
  await expect(page.getByRole("region", { name: "Одноразовые реквизиты" })).toHaveCount(0);

  // ADMIN: forced password change, no account controls, and backend account API is forbidden.
  const admin = await browser.newContext({ baseURL: "http://localhost:3000" });
  const adminPage = await admin.newPage();
  watchRuntimeErrors(adminPage, errors);
  await login(adminPage, adminUsername, adminTemporary);
  const adminPassword = await rotate(adminPage, "admin-stage3");
  await adminPage.goto(employeeUrl);
  await expect(adminPage.getByRole("button", { name: /Сбросить пароль|Заблокировать|Разблокировать/ })).toHaveCount(0);
  expect((await adminPage.request.post(`${apiBase}/employees/${employeeId}/account/block`)).status()).toBe(403);

  // Reset revokes both the current session and all older credentials.
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(employeeUrl);
  await page.getByRole("button", { name: "Сбросить пароль" }).click();
  const resetCredentials = page.getByRole("region", { name: "Одноразовые реквизиты" });
  const resetTemporary = await resetCredentials.getByText("Временный пароль:").locator("strong").innerText();
  expect(resetTemporary).not.toBe(adminTemporary);
  expect((await adminPage.request.get(`${apiBase}/auth/me`)).status()).toBe(401);
  await admin.close();

  const obsolete = await browser.newContext({ baseURL: "http://localhost:3000" });
  expect((await loginApi(obsolete, adminUsername, adminTemporary)).status()).toBe(401);
  expect((await loginApi(obsolete, adminUsername, adminPassword)).status()).toBe(401);
  await obsolete.close();

  const resetAdmin = await browser.newContext({ baseURL: "http://localhost:3000" });
  const resetAdminPage = await resetAdmin.newPage();
  watchRuntimeErrors(resetAdminPage, errors);
  await login(resetAdminPage, adminUsername, resetTemporary);
  const resetAdminPassword = await rotate(resetAdminPage, "admin-reset-stage3");

  // DIRECTOR block lifecycle revokes the new session and prevents login.
  await page.getByRole("button", { name: "Заблокировать" }).click();
  await expect(page.getByText("Доступ заблокирован.")).toBeVisible();
  expect((await resetAdminPage.request.get(`${apiBase}/auth/me`)).status()).toBe(401);
  await resetAdmin.close();
  const blocked = await browser.newContext({ baseURL: "http://localhost:3000" });
  const blockedLogin = await loginApi(blocked, adminUsername, resetAdminPassword);
  expect(blockedLogin.status()).toBe(403);
  expect((await blockedLogin.json()).error.code).toBe("USER_BLOCKED");
  await blocked.close();

  // Archive still confirms. Restore confirms too; cancel sends no restore request.
  let archivePrompt = "";
  page.once("dialog", async (dialog) => { archivePrompt = dialog.message(); await dialog.accept(); });
  await page.getByRole("button", { name: "Архивировать" }).click();
  expect(archivePrompt).toContain("Архивировать сотрудника");
  await expect(page.getByRole("button", { name: "Восстановить" })).toBeVisible();
  let restoreRequests = 0;
  const countRestore = (request: Request) => {
    if (request.method() === "POST" && request.url().endsWith(`/employees/${employeeId}/restore`)) restoreRequests += 1;
  };
  page.on("request", countRestore);
  let restorePrompt = "";
  page.once("dialog", async (dialog) => { restorePrompt = dialog.message(); await dialog.dismiss(); });
  await page.getByRole("button", { name: "Восстановить" }).click();
  expect(restorePrompt).toContain("не разблокирует связанного User автоматически");
  expect(restoreRequests).toBe(0);
  await expect(page.getByRole("button", { name: "Восстановить" })).toBeVisible();
  page.once("dialog", async (dialog) => { restorePrompt = dialog.message(); await dialog.accept(); });
  await page.getByRole("button", { name: "Восстановить" }).click();
  await expect(page.getByText("Карточка восстановлена. Доступ остаётся заблокированным, если был выдан.")).toBeVisible();
  page.off("request", countRestore);
  expect(restoreRequests).toBe(1);
  await expect(page.getByText("Заблокирован", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Разблокировать" })).toBeVisible();
  await page.getByRole("button", { name: "Разблокировать" }).click();
  await expect(page.getByText("Доступ восстановлен.")).toBeVisible();
  await page.getByRole("button", { name: "Заблокировать" }).click();
  await expect(page.getByText("Доступ заблокирован.")).toBeVisible();

  // Create two groups and a child for attendance and historical snapshot coverage.
  await page.goto("/groups");
  await page.getByLabel("Название группы").fill(groupAName);
  await page.getByRole("button", { name: "Создать группу" }).click();
  await expect(page).toHaveURL(/\/groups\/[a-f0-9-]+$/);
  const groupAId = page.url().split("/").pop()!;
  await page.goto("/groups");
  await page.getByLabel("Название группы").fill(groupBName);
  await page.getByRole("button", { name: "Создать группу" }).click();
  await expect(page).toHaveURL(/\/groups\/[a-f0-9-]+$/);
  const groupBId = page.url().split("/").pop()!;
  await page.goto("/children/new");
  await page.getByLabel("Фамилия").fill("Тестовый");
  await page.getByLabel("Имя").fill(childFirstName);
  await page.getByLabel("Дата рождения").fill("2020-01-01");
  await page.getByLabel("Группа", { exact: true }).selectOption(groupAId);
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page).toHaveURL(/\/children\/[a-f0-9-]+$/);
  const childId = page.url().split("/").pop()!;
  const childLabel = `Тестовый ${childFirstName}`;

  // Computed unknown -> present -> absent; all filters and date reset use real data.
  await page.goto("/attendance");
  await page.getByLabel("Дата").fill(attendanceDay);
  let row = page.locator(".attendance-list form").filter({ hasText: childLabel });
  await expect(row).toContainText("Без отметки");
  await row.getByLabel("Отметка").selectOption("present");
  await row.getByLabel("Приход").fill("08:30");
  await row.getByRole("button", { name: "Сохранить отметку" }).click();
  await expect(row).toContainText("Присутствует");
  await row.getByLabel("Отметка").selectOption("absent");
  await row.getByRole("button", { name: "Сохранить отметку" }).click();
  await expect(row).toContainText("Отсутствует");

  await page.getByLabel("Группа").selectOption(groupAId);
  await expect(row).toBeVisible();
  await page.getByLabel("Группа").selectOption(groupBId);
  await expect(page.locator(".attendance-list form").filter({ hasText: childLabel })).toHaveCount(0);
  await page.getByLabel("Группа").selectOption("");
  await page.getByLabel("Статус").selectOption("absent");
  await expect(page.locator(".attendance-list form").filter({ hasText: childLabel })).toBeVisible();
  await page.getByLabel("Статус").selectOption("present");
  await expect(page.locator(".attendance-list form").filter({ hasText: childLabel })).toHaveCount(0);
  await page.getByLabel("Статус").selectOption("all");
  await page.getByLabel("Ребёнок").selectOption(childId);
  await expect(page.locator(".attendance-list form")).toHaveCount(1);

  await page.getByLabel("Дата").fill(nextDay);
  await expect(page.getByLabel("Группа")).toHaveValue("");
  await expect(page.getByLabel("Статус")).toHaveValue("all");
  await expect(page.getByLabel("Ребёнок")).toHaveValue("");
  row = page.locator(".attendance-list form").filter({ hasText: childLabel });
  await expect(row).toContainText("Без отметки");
  await expect(row).not.toContainText("08:30");

  await page.getByLabel("Дата").fill(attendanceDay);
  await expectSuccess(await page.request.patch(`${apiBase}/children/${childId}`, { data: { group_id: groupBId } }));
  await page.reload();
  await page.getByLabel("Дата").fill(attendanceDay);
  await page.getByLabel("Группа").selectOption(groupAId);
  await expect(page.locator(".attendance-list form").filter({ hasText: childLabel })).toContainText(groupAName);
  await page.getByLabel("Группа").selectOption(groupBId);
  await expect(page.locator(".attendance-list form").filter({ hasText: childLabel })).toHaveCount(0);
  await page.setViewportSize({ width: 768, height: 900 });
  await expectNoHorizontalOverflow(page);

  // A real PARENT has no Stage 3 navigation, routes, or backend access.
  const guardiansResponse = await expectSuccess(await page.request.get(`${apiBase}/guardians?status=active&q=${encodeURIComponent("Представитель")}`));
  const guardians = await guardiansResponse.json() as { items: Array<{ id: string; account: object | null }> };
  const guardian = guardians.items.find((item) => item.account === null);
  expect(guardian).toBeTruthy();
  const parentCredentialsResponse = await expectSuccess(await page.request.post(`${apiBase}/guardians/${guardian!.id}/account`));
  const parentCredentials = await parentCredentialsResponse.json() as { account: { username: string }; temporary_password: string };
  const parent = await browser.newContext({ baseURL: "http://localhost:3000" });
  const parentPage = await parent.newPage();
  watchRuntimeErrors(parentPage, errors);
  await login(parentPage, parentCredentials.account.username, parentCredentials.temporary_password);
  await rotate(parentPage, "parent-stage3", /\/parent$/);
  await expect(parentPage).toHaveURL(/\/parent$/);
  await expect(parentPage.getByRole("link", { name: "Сотрудники" })).toHaveCount(0);
  await expect(parentPage.getByRole("link", { name: "Посещаемость" })).toHaveCount(0);
  await parentPage.goto("/employees");
  await expect(parentPage).toHaveURL(/\/parent$/);
  await parentPage.goto("/attendance");
  await expect(parentPage).toHaveURL(/\/parent$/);
  expect((await parentPage.request.get(`${apiBase}/employees`)).status()).toBe(403);
  expect((await parentPage.request.get(`${apiBase}/attendance?date=${attendanceDay}`)).status()).toBe(403);
  await parentPage.setViewportSize({ width: 390, height: 844 });
  await expectNoHorizontalOverflow(parentPage);
  await parent.close();

  // A second real tenant creates all four entity kinds; tenant A sees none of them.
  const other = await browser.newContext({ baseURL: "http://localhost:3000" });
  const otherPage = await other.newPage();
  watchRuntimeErrors(otherPage, errors);
  await login(otherPage, "stage3-other-director-demo", otherDirectorTemporary);
  await rotate(otherPage, "other-director-stage3");
  const foreignEmployeeResponse = await expectSuccess(await otherPage.request.post(`${apiBase}/employees`, { data: {
    first_name: "Другой", last_name: `Сотрудник${suffix}`, middle_name: null, position: "Администратор",
  } }));
  const foreignEmployee = await foreignEmployeeResponse.json() as { id: string };
  const foreignGroupResponse = await expectSuccess(await otherPage.request.post(`${apiBase}/groups`, { data: { name: `Чужая группа ${suffix}` } }));
  const foreignGroup = await foreignGroupResponse.json() as { id: string };
  const foreignChildResponse = await expectSuccess(await otherPage.request.post(`${apiBase}/children`, { data: {
    group_id: foreignGroup.id, first_name: "Другой", last_name: `Ребёнок${suffix}`, middle_name: null, birth_date: "2020-02-02",
  } }));
  const foreignChild = await foreignChildResponse.json() as { id: string };
  const foreignAttendanceResponse = await expectSuccess(await otherPage.request.post(`${apiBase}/attendance`, { data: {
    child_id: foreignChild.id, date: attendanceDay, status: "present", arrival_time: "09:00", departure_time: null,
  } }));
  const foreignAttendance = await foreignAttendanceResponse.json() as { record_id: string };
  await other.close();

  expect((await page.request.get(`${apiBase}/employees/${foreignEmployee.id}`)).status()).toBe(404);
  expect((await page.request.get(`${apiBase}/children/${foreignChild.id}`)).status()).toBe(404);
  expect((await page.request.get(`${apiBase}/groups/${foreignGroup.id}`)).status()).toBe(404);
  expect((await page.request.get(`${apiBase}/attendance/${foreignAttendance.record_id}`)).status()).toBe(404);
  expect((await page.request.post(`${apiBase}/attendance`, { data: {
    child_id: foreignChild.id, date: attendanceDay, status: "absent", arrival_time: null, departure_time: null,
  } })).status()).toBe(404);

  expect(errors).toEqual([]);
});
