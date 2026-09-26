/** QA3-02 UI regression with synthetic API responses; real API coverage remains in stage3.spec.ts. */
import { expect, test, type Page, type Route } from "@playwright/test";

const employeeId = "11111111-1111-4111-8111-111111111111";
const groupA = "22222222-2222-4222-8222-222222222222";
const groupB = "33333333-3333-4333-8333-333333333333";
const childA = "44444444-4444-4444-8444-444444444444";
const childB = "55555555-5555-4555-8555-555555555555";
const account = { id: "66666666-6666-4666-8666-666666666666", username: "staff-synthetic", role: "ADMIN", status: "active", must_change_password: true };
const employee = { id: employeeId, first_name: "Тест", last_name: "Синтетический", middle_name: null, position: "Сотрудник", status: "active", account: null as typeof account | null, archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
const cors = { "access-control-allow-origin": "http://localhost:3000", "access-control-allow-credentials": "true", "access-control-allow-methods": "GET,POST,PATCH,OPTIONS", "access-control-allow-headers": "content-type" };
const reply = (route: Route, body: object, status = 200) => route.fulfill({ status, contentType: "application/json", headers: cors, body: JSON.stringify(body) });
const failure = (route: Route) => reply(route, { error: { code: "INTERNAL_ERROR", message: "Hidden server details", field: null } }, 500);

async function mockAuth(page: Page) {
  await page.route("**/api/v1/auth/me", (route) => reply(route, {
    user: { id: "77777777-7777-4777-8777-777777777777", username: "director-synthetic", role: "DIRECTOR", status: "active", must_change_password: false },
    organization: { id: "88888888-8888-4888-8888-888888888888", name: "Синтетический сад" },
  }));
}

test("employee create and edit retain input after save failure", async ({ page }) => {
  await mockAuth(page);
  let createAttempts = 0; let editAttempts = 0;
  await page.route("**/api/v1/employees**", (route) => {
    const { pathname } = new URL(route.request().url());
    const method = route.request().method();
    if (pathname.endsWith("/employees") && method === "POST") {
      createAttempts += 1;
      return createAttempts === 1 ? failure(route) : reply(route, employee, 201);
    }
    if (pathname.endsWith(`/${employeeId}`) && method === "PATCH") {
      editAttempts += 1;
      return editAttempts === 1 ? failure(route) : reply(route, { ...employee, position: "Новая должность" });
    }
    if (pathname.endsWith(`/${employeeId}`) && method === "GET") return reply(route, employee);
    return reply(route, { items: [] });
  });
  await page.goto("/employees/new");
  await page.getByLabel("Фамилия").fill(employee.last_name);
  await page.getByLabel("Имя").fill(employee.first_name);
  await page.getByLabel("Должность").fill(employee.position);
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.locator(".alert-error")).toContainText("Не удалось выполнить запрос");
  await expect(page.getByLabel("Фамилия")).toHaveValue(employee.last_name);
  await expect(page.getByLabel("Должность")).toHaveValue(employee.position);
  await expect(page).toHaveURL(/\/employees\/new$/);
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page).toHaveURL(new RegExp(`/employees/${employeeId}$`));
  await page.getByRole("button", { name: "Изменить" }).click();
  await page.getByLabel("Должность").fill("Новая должность");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.locator(".alert-error")).toContainText("Не удалось выполнить запрос");
  await expect(page.getByLabel("Должность")).toHaveValue("Новая должность");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.getByRole("heading", { name: "Синтетический Тест" })).toBeVisible();
  await expect(page.getByText("Новая должность", { exact: true })).toBeVisible();
  expect([createAttempts, editAttempts]).toEqual([2, 2]);
});

test("create and reset credentials survive stale GET, then disappear on close, navigation and refresh", async ({ page }) => {
  await mockAuth(page);
  let accountPosts = 0; let detailGets = 0;
  await page.route("**/api/v1/employees/**", (route) => {
    const { pathname } = new URL(route.request().url());
    if (route.request().method() === "GET") { detailGets += 1; return reply(route, { ...employee, account: detailGets === 1 ? null : account }); }
    if (pathname.endsWith("/account") || pathname.endsWith("/reset-password")) {
      accountPosts += 1;
      return reply(route, { account, temporary_password: `temporary-synthetic-${accountPosts}` }, pathname.endsWith("/account") ? 201 : 200);
    }
    return failure(route);
  });
  await page.goto(`/employees/${employeeId}`);
  await expect(page.getByRole("button", { name: "Выдать доступ администратора" })).toBeVisible();
  await page.getByRole("button", { name: "Выдать доступ администратора" }).click();
  const credentials = page.getByRole("region", { name: "Одноразовые реквизиты" });
  await expect(credentials).toContainText("temporary-synthetic-1");
  await expect(credentials).toContainText(account.username);
  expect(detailGets).toBe(1);
  await credentials.getByRole("button", { name: "Закрыть и скрыть пароль" }).click();
  await expect(credentials).toHaveCount(0);
  await page.getByRole("button", { name: "Сбросить пароль" }).click();
  await expect(credentials).toContainText("temporary-synthetic-2");
  expect(detailGets).toBe(1);
  await page.getByRole("link", { name: "К сотрудникам" }).click();
  await expect(credentials).toHaveCount(0);
  await page.goto(`/employees/${employeeId}`);
  await expect(credentials).toHaveCount(0);
  await page.getByRole("button", { name: "Сбросить пароль" }).click();
  await expect(credentials).toContainText("temporary-synthetic-3");
  await page.reload();
  await expect(credentials).toHaveCount(0);
  expect(await page.evaluate(() => Object.keys(localStorage).length + Object.keys(sessionStorage).length)).toBe(0);
  expect(accountPosts).toBe(3);
});

test("attendance date clears old state and child choices track group and status", async ({ page }) => {
  await mockAuth(page);
  const rows = (date: string) => [
    { record_id: null, date, child: { id: childA, first_name: "Альфа", last_name: "Тестовый", middle_name: null, status: "active" }, group: { id: groupA, name: "Группа А" }, status: "present", arrival_time: null, departure_time: null },
    { record_id: null, date, child: { id: childB, first_name: "Бета", last_name: "Тестовый", middle_name: null, status: "active" }, group: { id: groupB, name: "Группа Б" }, status: "unknown", arrival_time: null, departure_time: null },
  ];
  let pendingOldDay = false;
  await page.route("**/api/v1/groups?**", (route) => reply(route, { items: [{ id: groupA, name: "Группа А" }, { id: groupB, name: "Группа Б" }] }));
  await page.route("**/api/v1/attendance?**", async (route) => {
    const url = new URL(route.request().url());
    const date = url.searchParams.get("date") ?? "2026-01-01";
    if (date === "2026-01-12") { pendingOldDay = true; await new Promise((resolve) => setTimeout(resolve, 350)); }
    const items = rows(date).filter((row) => (!url.searchParams.has("group_id") || row.group.id === url.searchParams.get("group_id")) && (!url.searchParams.has("status") || row.status === url.searchParams.get("status")));
    await reply(route, { items });
  });
  await page.goto("/attendance");
  const child = page.getByLabel("Ребёнок");
  await expect(child.locator("option")).toHaveCount(3);
  await child.selectOption(childB);
  await expect(page.locator(".attendance-list form")).toHaveCount(1);
  await page.getByLabel("Статус").selectOption("present");
  await expect(child).toHaveValue("");
  await expect(child.locator(`option[value="${childB}"]`)).toHaveCount(0);
  await page.getByLabel("Статус").selectOption("all");
  await expect(child.locator("option")).toHaveCount(3);
  await page.getByLabel("Группа").selectOption(groupA);
  await expect(child.locator(`option[value="${childB}"]`)).toHaveCount(0);
  await page.getByLabel("Дата").fill("2026-01-12");
  await expect(page.getByLabel("Группа")).toHaveValue("");
  await expect(page.getByLabel("Статус")).toHaveValue("all");
  await expect(child).toHaveValue("");
  await expect(page.locator(".attendance-list form")).toHaveCount(0);
  await expect.poll(() => pendingOldDay).toBe(true);
  await page.getByLabel("Дата").fill("2026-01-13");
  await expect(page.locator(".attendance-list form")).toHaveCount(2);
  await expect(page.locator(".attendance-list form").first()).toContainText("Тестовый Альфа");
  await page.waitForTimeout(450);
  await expect(page.locator(".attendance-list form")).toHaveCount(2);
  await expect(page.locator(".attendance-list form").first()).toContainText("Тестовый Альфа");
  await expect(child.locator("option")).toHaveCount(3);
});
