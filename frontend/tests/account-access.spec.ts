import { expect, test } from "@playwright/test";

const auth = { user: { id: "u1", username: "director", role: "DIRECTOR", status: "active", must_change_password: false }, organization: { id: "o1", name: "Сад" } };

test("login accepts login or email and forgot response stays generic", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { code: "UNAUTHORIZED", message: "", field: null } }) }));
  await page.route("**/api/v1/auth/forgot-password", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: "Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email." }) }));
  await page.goto("/login");
  await expect(page.getByLabel("Логин или email")).toBeVisible();
  await page.getByRole("link", { name: "Забыли пароль?" }).click();
  await page.getByLabel("Логин или email").fill("unknown@example.test");
  await page.getByRole("button", { name: "Отправить ссылку" }).click();
  await expect(page.getByText("Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email.")).toBeVisible();
});

for (const [path, heading, endpoint] of [
  ["/activate", "Активировать доступ", "/auth/activate"],
  ["/reset-password", "Новый пароль", "/auth/reset-password"],
] as const) {
  test(`${path} removes token fragment and never persists it`, async ({ page }) => {
    let body = "";
    await page.route(`**/api/v1${endpoint}`, async (route) => { body = route.request().postData() ?? ""; await route.fulfill({ status: 200, contentType: "application/json", body: '{"success":true}' }); });
    await page.goto(`${path}#token=secret-token-value-with-more-than-32-characters`);
    await expect(page).toHaveURL(new RegExp(`${path}$`));
    expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await page.getByLabel("Новый пароль").fill("safe-browser-password-123");
    await page.getByLabel("Повторите новый пароль").fill("different-browser-password-123");
    await page.getByRole("button", { name: "Сохранить пароль" }).click();
    await expect(page.getByText("Пароли не совпадают.")).toBeVisible();
    expect(body).toBe("");
    await page.getByLabel("Повторите новый пароль").fill("safe-browser-password-123");
    await page.getByRole("button", { name: "Сохранить пароль" }).click();
    expect(body).toContain("secret-token-value");
    expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  });
}

test("Access & Accounts renders statuses and has no plaintext password at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(auth) }));
  await page.route("**/api/v1/access-accounts", (route) => route.request().method() === "GET" ? route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
    parents: [{ profile_id: "g1", profile_type: "guardian", full_name: "Иванова Анна", context: "Родитель", username: "parent-one", role: "PARENT", masked_email: "a***@example.test", status: "invited", last_login_at: null, groups: [] }],
    teachers: [{ profile_id: "e1", profile_type: "employee", full_name: "Петров Пётр", context: "Воспитатель", username: "teacher-one", role: "TEACHER", masked_email: "p***@example.test", status: "activated", last_login_at: null, groups: ["Ромашка"] }], administrators: [], other_employees: [], blocked: [],
  }) }) : route.continue());
  await page.goto("/access-accounts");
  await expect(page.getByRole("heading", { name: "Доступ и аккаунты" })).toBeVisible();
  await expect(page.getByText("Приглашение отправлено", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Отправить приглашение снова" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Завершить все сеансы" })).toHaveCount(2);
  await expect(page.getByRole("button", { name: "Изменить роль" })).toBeVisible();
  await expect(page.getByText(/временный пароль/i)).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("bulk preflight shows every frozen classification", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(auth) }));
  await page.route("**/api/v1/access-accounts", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ parents: [{ profile_id: "g1", profile_type: "guardian", full_name: "Иванова Анна", context: "Родитель", username: null, role: null, masked_email: "a***@example.test", status: "no_account", last_login_at: null, groups: [] }], teachers: [], administrators: [], other_employees: [], blocked: [] }) }));
  await page.route("**/api/v1/access-accounts/parents/bulk-invite", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ preflight: { eligible: 1, missing_or_invalid_email: 2, activated: 3, already_invited: 4, failed_or_expired: 5, blocked: 6, archived: 7, no_active_linked_child: 8 }, results: [] }) }));
  await page.goto("/access-accounts");
  await page.getByText("Выбрать").click();
  await page.getByRole("button", { name: /Предварительный просмотр/ }).click();
  await expect(page.getByText(/ошибка или срок истёк.*5/)).toBeVisible();
  await expect(page.getByText(/архивные: 7/)).toBeVisible();
  await expect(page.getByText(/без активного связанного ребёнка: 8/)).toBeVisible();
});

test("employee category only preselects a visibly confirmed access role", async ({ page }) => {
  let createCalls = 0;
  let createBody = "";
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(auth) }));
  await page.route("**/api/v1/employees/e1", (route) => route.request().method() === "POST" ? (createCalls++, createBody = route.request().postData() ?? "", route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ username: "staff-one", role: "TEACHER", status: "sent" }) })) : route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "e1", first_name: "Пётр", last_name: "Петров", middle_name: null, position: "Воспитатель", category: "teacher", phone: null, email: "teacher@example.test", status: "active", account: null, archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }) }));
  await page.route("**/api/v1/management/employees/e1/profile", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ assignments: [], open_tasks: 0, overdue_tasks: 0 }) }));
  await page.route("**/api/v1/employees/e1/account", (route) => { createCalls++; createBody = route.request().postData() ?? ""; return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ username: "staff-one", role: "TEACHER", status: "sent" }) }); });
  await page.goto("/employees/e1");
  await expect(page.getByLabel("Роль доступа")).toHaveValue("TEACHER");
  await expect(page.getByText("Педагог (TEACHER)")).toBeVisible();
  expect(createCalls).toBe(0);
  await page.getByRole("button", { name: "Создать доступ с выбранной ролью" }).click();
  expect(JSON.parse(createBody)).toEqual({ role: "TEACHER" });
});

test("role change explains consequences and surfaces API failure", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(auth) }));
  await page.route("**/api/v1/employees/e2", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "e2", first_name: "Анна", last_name: "Петрова", middle_name: null, position: "Воспитатель", category: "teacher", phone: null, email: "teacher@example.test", status: "active", account: { id: "u2", username: "teacher-two", role: "TEACHER", status: "active", must_change_password: false }, archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }) }));
  await page.route("**/api/v1/management/employees/e2/profile", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ assignments: [], open_tasks: 0, overdue_tasks: 0 }) }));
  await page.route("**/api/v1/employees/e2/account/role", (route) => route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ error: { code: "ROLE_CHANGE_NOT_ALLOWED", message: "Изменение роли недоступно", field: null } }) }));
  page.on("dialog", async (dialog) => {
    expect(dialog.message()).toContain("Педагог (TEACHER) → Администратор (ADMIN)");
    expect(dialog.message()).toContain("сеансы будут завершены");
    expect(dialog.message()).toContain("назначения по группам — архивированы");
    await dialog.accept();
  });
  await page.goto("/employees/e2");
  await page.getByRole("button", { name: "Изменить роль" }).click();
  await expect(page.getByText("Изменение роли недоступно")).toBeVisible();
});
