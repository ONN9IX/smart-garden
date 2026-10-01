/** Demo-readiness regressions for active product surfaces. */
import { expect, test } from "@playwright/test";

const director = {
  user: { id: "00000000-0000-4000-8000-000000000701", username: "director-demo", role: "DIRECTOR", status: "active", must_change_password: false },
  organization: { id: "00000000-0000-4000-8000-000000000700", name: "Синтетический сад" },
};
const group = {
  id: "00000000-0000-4000-8000-000000000711", name: "Ромашка", status: "active",
  archived_at: null, created_at: "2026-09-30T08:00:00Z", updated_at: "2026-09-30T08:00:00Z",
};
const childId = "00000000-0000-4000-8000-000000000712";
const child = {
  id: childId, first_name: "Тестовый", last_name: "Ребёнок", middle_name: null,
  birth_date: "2020-01-01", status: "active", group: { id: group.id, name: group.name, status: "active" },
  guardians: [], archived_at: null, created_at: "2026-09-30T08:00:00Z", updated_at: "2026-09-30T08:00:00Z",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(director) }));
});

test("child card has no actions for OFF modules", async ({ page }) => {
  await page.route(`**/api/v1/children/${childId}`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(child) }));
  await page.route("**/api/v1/groups?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [group] }) }));
  await page.route("**/api/v1/guardians**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) }));
  await page.goto(`/children/${childId}`);
  await expect(page.getByRole("heading", { name: "Тестовый Ребёнок" })).toBeVisible();
  for (const label of ["Дневник", "Согласие на фото", "Происшествия группы"]) {
    await expect(page.getByRole("link", { name: label })).toHaveCount(0);
  }
});

test("management attendance defaults to garden-local server date", async ({ page }) => {
  await page.route("**/api/v1/dashboard/summary", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      date: "2026-10-01", active_children: 1, present: 0, absent: 0, unknown: 1,
      active_groups: 1, active_employees: 1, groups: [],
    }),
  }));
  await page.route("**/api/v1/groups?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [group] }) }));
  await page.route("**/api/v1/attendance?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) }));
  await page.goto("/attendance");
  await expect(page.getByLabel("Дата")).toHaveValue("2026-10-01");
});
