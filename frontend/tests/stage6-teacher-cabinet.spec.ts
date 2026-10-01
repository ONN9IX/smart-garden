/** Complete TEACHER cabinet daily flow and isolated navigation. */
import { expect, test } from "@playwright/test";

const group = { id: "00000000-0000-4000-8000-000000000611", name: "Ромашка" };
const child = { id: "00000000-0000-4000-8000-000000000612", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null, status: "active" };
const teacher = { user: { id: "00000000-0000-4000-8000-000000000601", username: "teacher-demo", role: "TEACHER", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(teacher) }));
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [group], schedule: [], attendance: [{ group_id: group.id, present: 1, absent: 0, unknown: 0 }], tasks: [], notifications: [], unread_communication_count: 1 }) }));
  await page.route("**/api/v1/teacher/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/children`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/guardians`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000613", child_id: child.id, first_name: "Тестовый", last_name: "Родитель", middle_name: null, relation_type: "mother", phone: "+70000000000", email: null }]) }));
  await page.route("**/api/v1/teacher/attendance?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: null, date: "2026-09-30", child, group, status: "unknown", arrival_time: null, departure_time: null }]) }));
  await page.route("**/api/v1/teacher/attendance", (route) => route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: null, departure_time: null }) }));
  for (const path of ["tasks", "notifications", "document-notices"]) await page.route(`**/api/v1/teacher/${path}`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
});

test("teacher completes the mobile daily flow without management navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/teacher");
  await expect(page.getByRole("heading", { name: "Кабинет воспитателя" })).toBeVisible();
  await expect(page.getByText("Новые сообщения")).toBeVisible();
  await expect(page.getByRole("link", { name: "Сотрудники" })).toHaveCount(0);
  await page.getByRole("link", { name: "Назначенные" }).click();
  await expect(page.getByText("Тестовый Ребёнок")).toBeVisible();
  await expect(page.getByText("+70000000000")).toBeVisible();
  await page.getByRole("link", { name: "Посещаемость" }).click();
  await expect(page.getByText("Тестовый Ребёнок")).toBeVisible();
  await page.getByRole("button", { name: "Пришёл" }).click();
  await page.getByRole("link", { name: "Ещё" }).click();
  await expect(page.getByRole("link", { name: "Дневник" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Фото" })).toBeVisible();
});

test("teacher empty assignment state remains usable", async ({ page }) => {
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [], schedule: [], attendance: [], tasks: [], notifications: [], unread_communication_count: 0 }) }));
  await page.goto("/teacher");
  await expect(page.getByText("0", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Назначенные" })).toBeVisible();
});
