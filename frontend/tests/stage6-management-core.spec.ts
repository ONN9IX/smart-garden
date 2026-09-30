/** Stage 6 management-core UX coverage using synthetic mocked Stage 1–4 responses only. */
import { expect, test, type Page, type Route } from "@playwright/test";

const cors = {
  "access-control-allow-origin": "http://localhost:3000",
  "access-control-allow-credentials": "true",
  "access-control-allow-methods": "GET,POST,PATCH,OPTIONS",
  "access-control-allow-headers": "content-type",
};
const groupId = "11111111-1111-4111-8111-111111111111";
const childId = "22222222-2222-4222-8222-222222222222";
const guardianId = "33333333-3333-4333-8333-333333333333";
const employeeId = "44444444-4444-4444-8444-444444444444";

const reply = (route: Route, body: object, status = 200) => route.fulfill({
  status, contentType: "application/json", headers: cors, body: JSON.stringify(body),
});

async function mockManagement(page: Page, role: "DIRECTOR" | "ADMIN" = "DIRECTOR") {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
    if (path.endsWith("/auth/me")) return reply(route, {
      user: { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", username: `${role.toLowerCase()}-synthetic`, role, status: "active", must_change_password: false },
      organization: { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name: "Синтетический сад" },
    });
    if (path.endsWith("/dashboard/summary")) return reply(route, {
      date: "2026-09-30", active_children: 3, present: 1, absent: 1, unknown: 1,
      active_groups: 1, active_employees: 1,
      groups: [{ id: groupId, name: "Солнышко", active_children: 3, present: 1, absent: 1, unknown: 1 }],
    });
    if (path.endsWith("/groups")) return reply(route, { items: [
      { id: groupId, name: "Солнышко", status: "active", archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
      { id: "55555555-5555-4555-8555-555555555555", name: "Ромашка", status: "active", archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
    ]});
    if (path.endsWith("/children")) return reply(route, { items: [{
      id: childId, first_name: "Ребёнок", last_name: "Синтетический", middle_name: null,
      birth_date: "2021-01-01", status: "active", group: { id: groupId, name: "Солнышко", status: "active" },
    }]});
    if (path.endsWith("/guardians")) return reply(route, { items: [{
      id: guardianId, first_name: "Родитель", last_name: "Синтетический", middle_name: null,
      phone: "+70000000000", email: null, status: "active", account: null,
    }]});
    if (path.endsWith("/employees")) return reply(route, { items: [{
      id: employeeId, first_name: "Админ", last_name: "Синтетический", middle_name: null,
      position: "Администратор", status: "active", account: role === "DIRECTOR"
        ? { id: "66666666-6666-4666-8666-666666666666", username: "admin-synthetic", role: "ADMIN", status: "active", must_change_password: false }
        : null,
    }]});
    if (path.endsWith("/attendance")) return reply(route, { items: [
      { record_id: null, date: "2026-09-30", child: { id: childId, first_name: "Ребёнок", last_name: "Синтетический", middle_name: null, status: "active" }, group: { id: groupId, name: "Солнышко" }, status: "present", arrival_time: "08:30:00", departure_time: null },
      { record_id: null, date: "2026-09-30", child: { id: "77777777-7777-4777-8777-777777777777", first_name: "Второй", last_name: "Синтетический", middle_name: null, status: "active" }, group: { id: groupId, name: "Солнышко" }, status: "unknown", arrival_time: null, departure_time: null },
    ]});
    if (path.endsWith("/announcements")) return reply(route, { items: [{
      id: "88888888-8888-4888-8888-888888888888", target_type: "group", group: { id: groupId, name: "Солнышко" },
      title: "Синтетическое объявление", body: "Тестовый текст", status: "active",
      created_by: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", updated_by: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      archived_at: null, created_at: "2026-09-30T08:00:00Z", updated_at: "2026-09-30T08:00:00Z",
    }]});
    if (path.endsWith("/audit")) return role === "DIRECTOR"
      ? reply(route, { items: [], limit: 50, offset: 0 })
      : reply(route, { error: { code: "FORBIDDEN", message: "Forbidden", field: null } }, 403);
    return reply(route, { error: { code: "NOT_FOUND", message: "Not found", field: null } }, 404);
  });
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("DIRECTOR management core exposes improved existing-domain UX without persistent browser data", async ({ page }) => {
  await mockManagement(page, "DIRECTOR");

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Оперативная сводка" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Быстрые действия" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Солнышко" })).toBeVisible();

  await page.goto("/groups");
  await page.getByLabel("Поиск по названию").fill("ром");
  await expect(page.getByText("Ромашка", { exact: true })).toBeVisible();
  await expect(page.getByText("Солнышко", { exact: true })).toHaveCount(0);

  await page.goto("/children");
  await expect(page.getByRole("heading", { name: "Дети" })).toBeVisible();
  await expect(page.getByText("Синтетический Ребёнок")).toBeVisible();

  await page.goto("/guardians");
  await expect(page.getByRole("heading", { name: "Родители и законные представители" })).toBeVisible();
  await expect(page.getByText("Синтетический Родитель")).toBeVisible();

  await page.goto("/employees");
  await page.getByLabel("Поиск по имени или должности").fill("администратор");
  await expect(page.getByText("Синтетический Админ")).toBeVisible();
  await expect(page.getByText(/ADMIN: активен/)).toBeVisible();

  await page.goto("/attendance");
  await expect(page.getByRole("heading", { name: "Посещаемость" })).toBeVisible();
  await expect(page.getByText("Всего", { exact: true })).toBeVisible();
  await expect(page.getByText("2", { exact: true }).first()).toBeVisible();
  await page.getByLabel("Статус").selectOption("unknown");
  await expect(page.getByRole("heading", { name: /Синтетический Второй/ })).toBeVisible();

  await page.goto("/announcements");
  await page.getByLabel("Получатели").selectOption("group");
  await expect(page.getByLabel("Группа")).toBeVisible();
  await page.getByLabel("Группа").selectOption(groupId);
  await expect(page.getByText("Синтетическое объявление")).toBeVisible();

  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Журнал аудита" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Сбросить фильтры" })).toBeVisible();

  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  for (const viewport of [{ width: 1280, height: 900 }, { width: 768, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto("/dashboard");
    await noOverflow(page);
  }
});

test("ADMIN keeps management core but cannot open Audit", async ({ page }) => {
  await mockManagement(page, "ADMIN");
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Оперативная сводка" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Аудит" })).toHaveCount(0);

  await page.goto("/employees");
  await expect(page.getByRole("heading", { name: "Сотрудники" })).toBeVisible();

  await page.goto("/audit");
  await expect(page).toHaveURL(/\/403$/);
});
