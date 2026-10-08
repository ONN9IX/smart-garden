import { expect, test, type Page, type Route } from "@playwright/test";

const cors = {
  "access-control-allow-origin": "http://localhost:3000",
  "access-control-allow-credentials": "true",
  "access-control-allow-methods": "GET,POST,PATCH,OPTIONS",
  "access-control-allow-headers": "content-type",
};
const ids = {
  group: "11111111-1111-4111-8111-111111111111",
  groupWithoutSchedule: "22222222-2222-4222-8222-222222222222",
  notification: "33333333-3333-4333-8333-333333333333",
};

const today = {
  date: "2026-10-07", active_children: 12, present: 8, absent: 2, unknown: 2,
  active_groups: 2, active_employees: 4, groups_without_active_teacher_assignment: 1,
  open_tasks: 3, overdue_tasks: 1, open_incidents: 0, unread_notifications: 1,
  groups: [
    { group_id: ids.group, group_name: "Солнышко", active_children: 7, present: 5, absent: 1, unknown: 1, has_active_teacher: true, has_active_weekly_schedule: true },
    { group_id: ids.groupWithoutSchedule, group_name: "Ромашка", active_children: 5, present: 3, absent: 1, unknown: 1, has_active_teacher: false, has_active_weekly_schedule: false },
  ],
  attention_items: [
    { kind: "attendance_missing", entity_type: "attendance", entity_id: ids.group, count: 1 },
    { kind: "group_without_teacher", entity_type: "group", entity_id: ids.groupWithoutSchedule, count: null },
    { kind: "group_without_schedule", entity_type: "group", entity_id: ids.groupWithoutSchedule, count: null },
    { kind: "tasks_overdue", entity_type: "teacher_task", entity_id: null, count: 1 },
    { kind: "notifications_unread", entity_type: "notification", entity_id: ids.notification, count: 1 },
  ],
};

async function mockToday(page: Page, role: "DIRECTOR" | "ADMIN") {
  await page.route("**/api/v1/**", async (route: Route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
    if (path.endsWith("/auth/me")) return route.fulfill({ status: 200, contentType: "application/json", headers: cors,
      body: JSON.stringify({ user: { id: "44444444-4444-4444-8444-444444444444", username: role.toLowerCase() + "-synthetic", role, status: "active", must_change_password: false }, organization: { id: "55555555-5555-4555-8555-555555555555", name: "Синтетический сад" } }) });
    if (path.endsWith("/management/today")) return route.fulfill({ status: 200, contentType: "application/json", headers: cors, body: JSON.stringify(today) });
    return route.fulfill({ status: 404, contentType: "application/json", headers: cors, body: JSON.stringify({ error: { code: "NOT_FOUND", message: "Не найдено", field: null } }) });
  });
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("DIRECTOR gets the v2 navigation and a single-read exception-first Today", async ({ page }) => {
  await mockToday(page, "DIRECTOR");
  const todayRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/management/today")) todayRequests.push(request.url());
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "Сегодня", exact: true })).toBeVisible();
  await expect(page.getByText("Синтетический сад", { exact: true })).toBeVisible();
  await expect(page.getByText("7 октября 2026 г.")).toBeVisible();
  const navLabels = await page.locator(".management-sidebar nav a").allTextContents();
  expect(navLabels).toEqual(["Сегодня", "Группы", "Дети", "Родители", "Сотрудники", "Доступ и аккаунты", "Посещаемость", "Расписание", "Задачи", "Сообщения", "Объявления", "Уведомления", "Журнал действий", "Настройки"]);
  await expect(page.getByRole("link", { name: "Воспитатели", exact: true })).toHaveCount(0);

  for (const label of ["В саду", "Отсутствуют", "Не отмечены", "Активные группы", "Без воспитателя", "Просроченные задачи"]) {
    await expect(page.getByRole("link", { name: new RegExp(label) })).toBeVisible();
  }
  await expect(page.getByRole("heading", { name: "Группы сегодня" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Солнышко", exact: true })).toHaveAttribute("href", `/groups/${ids.group}`);
  await expect(page.getByText("Ромашка: нет активного воспитателя")).toBeVisible();
  await expect(page.getByText("Ромашка: нет недельного расписания")).toBeVisible();
  await expect(page.getByText("Просрочено задач: 1")).toBeVisible();
  await expect(page.getByText(new RegExp(ids.group))).toHaveCount(0);
  expect(todayRequests).toHaveLength(1);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  const mobileNav = page.getByRole("navigation", { name: "Мобильная навигация" });
  await expect(mobileNav).toBeVisible();
  await expect(mobileNav.locator("a, button")).toHaveCount(5);
  await expect(mobileNav.getByText("Сегодня", { exact: true })).toBeVisible();
  await expect(mobileNav.getByText("Люди", { exact: true })).toBeVisible();
  await expect(mobileNav.getByText("Работа", { exact: true })).toBeVisible();
  await expect(mobileNav.getByText("Связь", { exact: true })).toBeVisible();
  await mobileNav.getByRole("button", { name: /Ещё/ }).click();
  await expect(page.getByRole("link", { name: "Журнал действий" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Настройки" })).toBeVisible();
  await noOverflow(page);
});

test("ADMIN mobile More exposes account context without director controls", async ({ page }) => {
  await mockToday(page, "ADMIN");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  const mobileNav = page.getByRole("navigation", { name: "Мобильная навигация" });
  await expect(mobileNav.locator("a, button")).toHaveCount(5);
  await mobileNav.getByRole("button", { name: /Ещё/ }).click();
  await expect(page.getByText("admin-synthetic · Администратор")).toBeVisible();
  await expect(page.getByRole("link", { name: "Журнал действий" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Настройки", exact: true })).toHaveCount(0);
  await noOverflow(page);
});
