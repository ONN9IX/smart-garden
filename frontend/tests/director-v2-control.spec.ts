import { expect, test, type Page, type Route } from "@playwright/test";

const userId = "11111111-1111-4111-8111-111111111111";
const groupId = "22222222-2222-4222-8222-222222222222";
const notificationId = "33333333-3333-4333-8333-333333333333";
const cors = { "access-control-allow-origin": "http://localhost:3000", "access-control-allow-credentials": "true",
  "access-control-allow-methods": "GET,POST,PATCH,OPTIONS", "access-control-allow-headers": "content-type" };
const reply = (route: Route, value: object, status = 200) => route.fulfill({
  status, contentType: "application/json", headers: cors, body: JSON.stringify(value),
});

async function mock(page: Page, role: "DIRECTOR" | "ADMIN" = "DIRECTOR") {
  let present = true;
  let viewed = false;
  let snoozed: string | null = null;
  let notifications = true;
  let settings = { id: userId, name: "Синтетический сад", timezone: "Europe/Moscow" };
  let preferences = { show_informational_notifications: true, attendance_checkpoint_time: null as string | null,
    schedule_missing_alert_enabled: true };
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    if (method === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
    if (path.endsWith("/auth/me")) return reply(route, { user: { id: userId, username: "synthetic-user", role,
      status: "active", must_change_password: false }, organization: { id: userId, name: settings.name } });
    if (path.endsWith("/management/control")) return reply(route, {
      alerts: present ? [{ alert_key: `group_without_teacher:${groupId}`, kind: "group_without_teacher",
        priority: "important", title: "Нет воспитателя", context: "Ромашка", action_href: `/groups/${groupId}`,
        viewed_at: viewed ? "2026-10-12T12:00:00Z" : null, snoozed_until: snoozed }] : [],
      event_notifications: notifications ? [{ id: notificationId, title: "Назначена задача", priority: "important",
        read_at: null, created_at: "2026-10-12T10:00:00Z" }] : [],
      summary: { new: present && !viewed && !snoozed ? 1 : 0, important: present && !snoozed ? 1 : 0,
        snoozed: present && snoozed ? 1 : 0 },
    });
    if (path.endsWith("/management/control/alerts/view")) { viewed = true; return reply(route, {}); }
    if (path.endsWith("/management/control/alerts/snooze")) { viewed = true; snoozed = "2099-10-13T08:00:00Z"; return reply(route, {}); }
    if (path.endsWith(`/management/notifications/${notificationId}/read`)) { notifications = false; return reply(route, {}); }
    if (path.endsWith("/audit/journal")) return role === "ADMIN" ? reply(route, { error: { code: "FORBIDDEN" } }, 403) : reply(route, {
      items: [{ id: notificationId, created_at: "2026-10-12T10:00:00Z", category: "groups",
        actor: { id: userId, display_name: "Синтетическая Анна", role: "TEACHER" },
        summary: "Изменено Ромашка", target: { type: "group", display_name: "Ромашка" },
        safe_changes: ["Изменено: название"] }],
      actors: [{ id: userId, display_name: "Синтетическая Анна", role: "TEACHER" }], limit: 25, offset: 0,
    });
    if (path.endsWith("/management/settings")) {
      if (method === "PATCH") settings = { ...settings, ...route.request().postDataJSON() };
      return reply(route, settings);
    }
    if (path.endsWith("/management/notification-settings")) {
      if (method === "PATCH") preferences = { ...preferences, ...route.request().postDataJSON() };
      return reply(route, preferences);
    }
    if (path.endsWith("/management/security-status")) return reply(route, { blocked_accounts: 2, failed_or_expired_parent_invites: 1 });
    return reply(route, { error: { code: "NOT_FOUND" } }, 404);
  });
  return { resolve: () => { present = false; }, preferences: () => preferences };
}

test("Control keeps live alerts apart from recipient events and resolves them at 390px", async ({ page }) => {
  const state = await mock(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/notifications");
  await expect(page.getByRole("heading", { name: "Нет воспитателя" })).toBeVisible();
  await expect(page.getByText("Назначена задача")).toBeVisible();
  await page.getByRole("button", { name: "На 1 час" }).click();
  await expect(page.getByRole("heading", { name: "Отложенные" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Отложенные" })).toBeVisible();
  state.resolve(); await page.reload();
  await expect(page.getByRole("heading", { name: "Отложенные" })).toHaveCount(0);
  await expect(page.getByText("Назначена задача")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("Journal shows human teacher events without raw details and denies ADMIN", async ({ page }) => {
  await mock(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Журнал действий" })).toBeVisible();
  await expect(page.getByRole("paragraph").filter({ hasText: "Синтетическая Анна · Воспитатель" })).toBeVisible();
  await expect(page.getByText(groupId)).toHaveCount(0);
  await page.getByLabel("Категория").selectOption("groups");
  await expect(page.getByText("Изменено Ромашка")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const admin = await page.context().newPage(); await mock(admin, "ADMIN");
  await admin.goto("/audit"); await expect(admin).toHaveURL(/\/403$/);
  await admin.close();
});

test("Settings confirms timezone impact and saves notification policy at 390px", async ({ page }) => {
  const state = await mock(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/settings");
  await expect(page.getByText("Нет подключённых интеграций.")).toBeVisible();
  await expect(page.getByText("Заблокированных аккаунтов: 2")).toBeVisible();
  await expect(page.getByRole("link", { name: /Открыть доступы и аккаунты/ })).toHaveAttribute("href", "/access-accounts");
  await page.getByLabel("Часовой пояс IANA").fill("Europe/Amsterdam");
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByLabel("Часовой пояс IANA")).toHaveValue("Europe/Amsterdam");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByText("Настройки сохранены.")).toBeVisible();
  await page.getByLabel("Показывать информационные уведомления").uncheck();
  await page.getByRole("button", { name: "Сохранить уведомления" }).click();
  expect(state.preferences().show_informational_notifications).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
