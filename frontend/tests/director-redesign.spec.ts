import { expect, test, type Page, type Route } from "@playwright/test";

const groupId = "11111111-1111-4111-8111-111111111111";
const childA = "22222222-2222-4222-8222-222222222222";
const childB = "33333333-3333-4333-8333-333333333333";
const cors = { "access-control-allow-origin": "http://localhost:3000", "access-control-allow-credentials": "true", "access-control-allow-methods": "GET,POST,PATCH,OPTIONS", "access-control-allow-headers": "content-type" };
const reply = (route: Route, body: object, status = 200) => route.fulfill({ status, contentType: "application/json", headers: cors, body: JSON.stringify(body) });
const group = { id: groupId, name: "Синтетическая группа", status: "active", archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
const child = (id: string, first_name: string) => ({ id, first_name, last_name: "Тестовый", middle_name: null, birth_date: "2021-04-05", status: "active", group, guardians: [], archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" });

async function mock(page: Page, deniedStatus?: 403 | 404, role: "DIRECTOR" | "ADMIN" | "TEACHER" | "PARENT" = "DIRECTOR") {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
    if (path.endsWith("/auth/me")) return reply(route, { user: { id: "44444444-4444-4444-8444-444444444444", username: "user-synthetic", role, status: "active", must_change_password: false }, organization: { id: "55555555-5555-4555-8555-555555555555", name: "Синтетический сад" } });
    if (path.endsWith("/management/today")) return reply(route, { date: "2026-10-07", active_children: 2, present: 1, on_site: 1, departed: 0, absent: 0, unknown: 1, needs_arrival: 0, active_groups: 1, active_employees: 0, groups_without_active_teacher_assignment: 1, open_tasks: 0, overdue_tasks: 0, open_incidents: 0, unread_notifications: 0, groups: [{ group_id: groupId, group_name: group.name, active_children: 2, present: 1, on_site: 1, departed: 0, absent: 0, unknown: 1, needs_arrival: 0, has_active_teacher: false, has_active_weekly_schedule: false }], attention_items: [{ kind: "group_without_teacher", entity_type: "group", entity_id: groupId, count: null }] });
    if (path.endsWith("/management/groups/overview")) return reply(route, { items: [{ group, active_children: 2, present: 1, on_site: 1, departed: 0, absent: 0, unknown: 1, needs_arrival: 0, active_teacher_names: [], has_active_weekly_schedule: false, open_tasks: 0, overdue_tasks: 0 }] });
    if (path.endsWith(`/management/groups/${groupId}/profile`)) return reply(route, { group, local_date: "2026-10-07", active_children: 2, present: 1, on_site: 1, departed: 0, absent: 0, unknown: 1, needs_arrival: 0, active_teacher_count: 0, parent_count: 0, active_schedule_count: 0, open_tasks: 0, overdue_tasks: 0, children: [], employees: [], parents: [], schedule: [] });
    if (path.endsWith("/groups")) return reply(route, { items: [group] });
    if (path.endsWith("/guardians")) return reply(route, { items: [] });
    if (path.endsWith("/children")) return reply(route, { items: [child(childA, "Первый"), child(childB, "Второй")] });
    if (path.endsWith(`/children/${childA}`)) { await new Promise((resolve) => setTimeout(resolve, 500)); return reply(route, child(childA, "Первый")); }
    if (path.endsWith(`/children/${childB}`)) return deniedStatus ? reply(route, { error: { code: deniedStatus === 403 ? "FORBIDDEN" : "NOT_FOUND", message: "Доступ закрыт" } }, deniedStatus) : reply(route, child(childB, "Второй"));
    if (path.endsWith("/management/control")) return reply(route, { alerts: [], event_notifications: [], summary: { new: 0, important: 0, snoozed: 0 } });
    if (path.endsWith("/audit/journal")) return reply(route, { items: [], actors: [], limit: 25, offset: 0 });
    return reply(route, { error: { code: "NOT_FOUND" } }, 404);
  });
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("director screens reflow at desktop, tablet, mobile and 200% zoom", async ({ page }, testInfo) => {
  await mock(page);
  for (const width of [1440, 768, 390, 720]) {
    await page.setViewportSize({ width, height: 900 });
    for (const [route, heading] of [["/dashboard", "Сегодня"], ["/groups", "Группы"], ["/children", "Дети"], ["/notifications", "Контроль"], ["/audit", "Журнал действий"]]) {
      await page.goto(route);
      await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
      await noOverflow(page);
      if (width === 1440 || width === 390) {
        await page.screenshot({ path: testInfo.outputPath(`${route.slice(1)}-${width}.png`), fullPage: true });
      }
      if (width === 720) {
        await page.screenshot({ path: testInfo.outputPath(`${route.slice(1)}-200-percent.png`), fullPage: true });
      }
    }
  }
});

test("group and child profiles retain authorized actions and responsive sections", async ({ page }, testInfo) => {
  await mock(page);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`/groups/${groupId}`);
    await expect(page.getByRole("heading", { name: group.name, exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Архивировать" })).toBeVisible();
    await noOverflow(page);
    await page.screenshot({ path: testInfo.outputPath(`group-profile-${width}.png`), fullPage: true });
    await page.goto(`/children/${childB}`);
    await expect(page.getByRole("heading", { name: "Тестовый Второй" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Изменить данные" })).toBeVisible();
    await noOverflow(page);
    await page.screenshot({ path: testInfo.outputPath(`child-profile-${width}.png`), fullPage: true });
  }
});

test("a forbidden child response never reveals the previous child", async ({ page }) => {
  await mock(page, 403);
  await page.goto(`/children/${childA}`);
  await page.goto(`/children/${childB}`);
  await expect(page.getByText("Первый", { exact: false })).toHaveCount(0);
  await expect(page.getByText("Второй", { exact: false })).toHaveCount(0);
  await expect(page.locator(".alert-error")).toBeVisible();
});

test("foreign child 404 clears personal data", async ({ page }) => {
  await mock(page, 404);
  await page.goto(`/children/${childB}`);
  await expect(page.getByRole("heading", { name: "Тестовый Второй" })).toHaveCount(0);
  await expect(page.locator(".alert-error")).toBeVisible();
});

for (const role of ["ADMIN", "TEACHER", "PARENT"] as const) {
  test(`${role} cannot open director journal`, async ({ page }) => {
    await mock(page, undefined, role);
    await page.goto("/audit");
    await expect(page).toHaveURL(role === "ADMIN" ? /\/403$/ : role === "TEACHER" ? /\/teacher$/ : /\/parent$/);
    await expect(page.getByRole("heading", { name: "Журнал действий" })).toHaveCount(0);
  });
}
