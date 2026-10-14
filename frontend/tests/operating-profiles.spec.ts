import { expect, test } from "@playwright/test";

const context = {
  user: { id: "owner-1", username: "coach-owner", role: "DIRECTOR", status: "active", must_change_password: false },
  organization: { id: "org-1", name: "Секция Пример", operating_profile: "GYMNASTICS" },
};
const group = { id: "group-1", name: "Юные гимнастки" };
const today = { date: "2026-10-13", groups: [group], schedule: [{ id: "schedule-1", group_id: group.id, weekday: 2, start_time: "10:00:00", end_time: "11:00:00", title: "Основная тренировка" }], attendance: [{ group_id: group.id, active_children: 3, present: 1, on_site: 1, departed: 0, absent: 1, unknown: 1, needs_arrival: 0 }], tasks: [], notifications: [], unread_communication_count: 0 };

test("gymnastics director sees assigned-coach Today workflow and profile terms", async ({ page }) => {
  await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(context) }));
  await page.route("**/api/v1/employees/me/coach-profile", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "employee-1", first_name: "Алексей", last_name: "Примеров", middle_name: null, position: "Тренер", category: "teacher", phone: null, email: null, status: "active", account: { id: "owner-1", username: "coach-owner", role: "DIRECTOR", status: "active", must_change_password: false }, archived_at: null, created_at: "2026-10-13T00:00:00Z", updated_at: "2026-10-13T00:00:00Z" }) }));
  await page.route("**/api/v1/teacher/today", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(today) }));
  await page.route("**/api/v1/auth/logout", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) }));
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Сегодня" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Юные гимнастки" })).toBeVisible();
  await expect(page.getByText("Спортсменов: 3 · присутствуют: 1 · отсутствуют: 1 · без отметки: 1")).toBeVisible();
  await expect(page.getByRole("link", { name: "Расписание", exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Сообщения", exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Посещаемость", exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Группы", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Первоначальная настройка", exact: true })).toBeVisible();
  await expect(page.locator('a[href="/teacher/announcements"]')).toHaveCount(0);
  await expect(page.locator('a[href="/teacher/more"]')).toHaveCount(0);
  await page.goto("/teacher");
  await expect(page.getByRole("heading", { name: "Юные гимнастки" })).toBeVisible();
});

test("gymnastics director can correct attendance for a past date", async ({ page }) => {
  await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(context) }));
  await page.route("**/api/v1/employees/me/coach-profile", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "employee-1", first_name: "Алексей", last_name: "Примеров", middle_name: null, position: "Тренер", category: "teacher", phone: null, email: null, status: "active", account: { id: "owner-1", username: "coach-owner", role: "DIRECTOR", status: "active", must_change_password: false }, archived_at: null, created_at: "2026-10-13T00:00:00Z", updated_at: "2026-10-13T00:00:00Z" }) }));
  await page.route("**/api/v1/teacher/today", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(today) }));
  await page.route("**/api/v1/teacher/groups", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group]) }));
  await page.route("**/api/v1/teacher/attendance?**", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: "attendance-1", date: "2026-10-12", child: { id: "child-1", first_name: "Синтетическая", last_name: "Спортсменка" }, group, status: "absent", arrival_time: null, departure_time: null }]) }));
  let savedStatus = "";
  await page.route("**/api/v1/teacher/attendance/group-day", async route => {
    savedStatus = route.request().postDataJSON().items[0].status;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });
  await page.goto("/teacher/attendance");
  await page.getByLabel("Дата").fill("2026-10-12");
  await page.getByRole("button", { name: "Присутствует", exact: true }).click();
  await expect.poll(() => savedStatus).toBe("present");
});
