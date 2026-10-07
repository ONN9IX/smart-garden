/** Synthetic-only coverage for DIRECTOR-V2-B People and Group workflows. */
import { expect, test, type Page, type Route } from "@playwright/test";

const groupId = "11111111-1111-4111-8111-111111111111";
const childId = "22222222-2222-4222-8222-222222222222";
const guardianId = "33333333-3333-4333-8333-333333333333";
const cors = { "access-control-allow-origin": "http://localhost:3000", "access-control-allow-credentials": "true", "access-control-allow-methods": "GET,POST,PATCH,OPTIONS", "access-control-allow-headers": "content-type" };
const reply = (route: Route, body: object, status = 200) => route.fulfill({ status, contentType: "application/json", headers: cors, body: JSON.stringify(body) });
const group = { id: groupId, name: "Синтетическая группа", status: "active", archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
const child = { id: childId, first_name: "Синтетический", last_name: "Ребёнок", middle_name: null, birth_date: "2021-04-05", status: "active", group: { id: groupId, name: group.name, status: "active" }, guardians: [], archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };

async function mockApi(page: Page) {
  let familyPosts = 0;
  let groupOverviewGets = 0;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (request.method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors });
    if (path.endsWith("/auth/me")) return reply(route, {
      user: { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", username: "director-synthetic", role: "DIRECTOR", status: "active", must_change_password: false },
      organization: { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name: "Синтетический сад" },
    });
    if (path.endsWith("/groups") && request.method() === "GET") return reply(route, { items: [group] });
    if (path.endsWith("/management/people/duplicates")) return reply(route, { matches: [{ id: childId, full_name: "Существующий синтетический ребёнок", context: "Синтетическая группа" }] });
    if (path.endsWith("/management/people/guardian-search")) return reply(route, { matches: [{ id: guardianId, full_name: "Синтетический представитель", phone: null, email: null, account_status: null }] });
    if (path.endsWith("/management/families") && request.method() === "POST") { familyPosts += 1; return reply(route, child, 201); }
    if (path.endsWith("/management/groups/overview")) {
      groupOverviewGets += 1;
      return reply(route, { items: [{ group, active_children: 2, present: 1, absent: 0, unknown: 1, active_teacher_names: [], has_active_weekly_schedule: false, open_tasks: 1, overdue_tasks: 1 }] });
    }
    if (path.endsWith("/management/groups/" + groupId + "/profile")) return reply(route, {
      group, local_date: "2026-10-07", active_children: 2, present: 1, absent: 0, unknown: 1,
      active_teacher_count: 0, parent_count: 1, active_schedule_count: 0, open_tasks: 1, overdue_tasks: 1,
      children: [{ id: childId, first_name: "Синтетический", last_name: "Ребёнок", middle_name: null, status: "active", today_attendance: "unknown", active_guardian_count: 1 }], employees: [],
      parents: [], schedule: [],
    });
    return reply(route, { error: { code: "NOT_FOUND", message: "Запись не найдена.", field: null } }, 404);
  });
  return { getFamilyPosts: () => familyPosts, getGroupOverviewGets: () => groupOverviewGets };
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("family wizard warns about duplicates, lets the user continue separately and creates relations atomically", async ({ page }) => {
  const counters = await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/children/new");
  await page.getByLabel("Фамилия *").fill("Иванов");
  await page.getByLabel("Имя *").fill("Кирилл");
  await page.getByLabel("Дата рождения *").fill("2021-04-05");
  await page.getByLabel("Группа *").selectOption(groupId);
  await page.getByRole("button", { name: "Далее: представители" }).click();
  await expect(page.getByText("Существующий синтетический ребёнок")).toBeVisible();
  await page.getByRole("button", { name: "Продолжить с отдельной карточкой" }).click();
  await page.getByLabel("Найти существующего представителя").fill("Синтетический");
  await page.getByRole("button", { name: "Найти" }).click();
  await page.getByRole("button", { name: "Добавить" }).first().click();
  await page.getByRole("button", { name: "Далее: проверка" }).click();
  await expect(page.getByText(/одной транзакцией/)).toBeVisible();
  await noOverflow(page);
  await page.getByRole("button", { name: "Создать ребёнка и связи" }).click();
  await expect(page).toHaveURL(`/children/${childId}`);
  expect(counters.getFamilyPosts()).toBe(1);
});

test("Group aggregate loads in one collection request and stays readable at 390px", async ({ page }) => {
  const counters = await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/groups");
  await expect(page.getByText("Детей: 2")).toBeVisible();
  await expect(page.getByText(/Расписание: не задано/)).toBeVisible();
  await expect(page.getByText("Требует внимания")).toBeVisible();
  await noOverflow(page);
  expect(counters.getGroupOverviewGets()).toBe(1);
});
