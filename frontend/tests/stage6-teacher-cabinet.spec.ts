/** Enabled TEACHER cabinet flow plus deferred-module visibility gates. */
import { expect, test } from "@playwright/test";

const group = { id: "00000000-0000-4000-8000-000000000611", name: "Ромашка" };
const child = { id: "00000000-0000-4000-8000-000000000612", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null, status: "active" };
const guardian = { id: "00000000-0000-4000-8000-000000000613", child_id: child.id, first_name: "Тестовый", last_name: "Родитель", middle_name: null, relation_type: "mother", phone: "+70000000000", email: null, can_message: true };
const thread = { id: "00000000-0000-4000-8000-000000000615", thread_type: "direct", group_id: group.id, audience: "all", child_id: child.id, guardian_id: guardian.id, created_at: "2026-09-30T09:00:00Z" };
const teacher = { user: { id: "00000000-0000-4000-8000-000000000601", username: "teacher-demo", role: "TEACHER", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(teacher) }));
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [group], schedule: [], attendance: [{ group_id: group.id, present: 1, absent: 0, unknown: 0 }], tasks: [], notifications: [], unread_communication_count: 1 }) }));
  await page.route("**/api/v1/teacher/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/children`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/guardians`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([guardian]) }));
  await page.route("**/api/v1/teacher/attendance?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: null, date: "2026-09-30", child, group, status: "unknown", arrival_time: null, departure_time: null }]) }));
  await page.route("**/api/v1/teacher/attendance", (route) => route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: null, departure_time: null }) }));
  await page.route("**/api/v1/teacher/attendance/arrival", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: "08:15:00", departure_time: null }) }));
  await page.route("**/api/v1/teacher/attendance/departure", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: "08:15:00", departure_time: "17:05:00" }) }));
  await page.route("**/api/v1/teacher/tasks", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.route("**/api/v1/teacher/notifications", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
});

test("teacher completes daily flow and sees only enabled modules", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/teacher");
  await expect(page.getByRole("heading", { name: "Кабинет воспитателя" })).toBeVisible();
  await expect(page.getByLabel("ПРОМАКС — главная")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("link", { name: "Мои группы", exact: true }).click();
  await expect(page.getByText("Тестовый Ребёнок")).toBeVisible();
  await expect(page.getByText("Мама · можно написать")).toBeVisible();
  await page.getByRole("link", { name: "Посещаемость" }).click();
  await expect(page.getByLabel("Дата")).toHaveValue("2026-09-30");
  await expect(page.getByText("Не отмечен")).toBeVisible();
  const arrival = page.waitForRequest("**/api/v1/teacher/attendance/arrival");
  await page.getByRole("button", { name: "Пришёл" }).click();
  expect((await arrival).postDataJSON()).toEqual({ child_id: child.id });
  await page.getByRole("link", { name: "Задачи и уведомления" }).click();
  await expect(page.getByRole("heading", { name: "Задачи и уведомления" })).toBeVisible();
  for (const label of ["Дневник", "Опросы", "События", "Фото"]) {
    await expect(page.getByRole("link", { name: label })).toHaveCount(0);
  }
  await expect(page.getByText("Документы к ознакомлению")).toHaveCount(0);
});

test("teacher keeps schedule, communications, announcements, tasks and notifications", async ({ page }) => {
  await page.route("**/api/v1/teacher/schedule?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000616", group_id: group.id, weekday: 2, start_time: "09:00:00", end_time: "09:30:00", title: "Музыка" }]) }));
  await page.goto("/teacher/schedule");
  await expect(page.getByText("Музыка")).toBeVisible();

  const v2Thread = { ...thread, group_name: group.name, child_name: "Ребёнок Тестовый", teacher_employee_id: "00000000-0000-4000-8000-000000000631", teacher_name: "Воспитатель Тестовый", last_message_id: "00000000-0000-4000-8000-000000000618", last_message_at: "2026-09-30T10:00:00Z", preview: "Сообщение родителя", unread_count: 1 };
  await page.route("**/api/v1/teacher/communications/v2/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([v2Thread]) }));
  await page.route("**/api/v1/teacher/communications/v2/threads/*/messages", (route) => route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, contentType: "application/json", body: route.request().method() === "POST" ? JSON.stringify({ id: "00000000-0000-4000-8000-000000000617", thread_id: thread.id, sender_user_id: teacher.user.id, sender_role: "TEACHER", sender_name: "Воспитатель Тестовый", body: "Ответ воспитателя", created_at: "2026-09-30T10:10:00Z" }) : JSON.stringify([{ id: "00000000-0000-4000-8000-000000000618", thread_id: thread.id, sender_user_id: "00000000-0000-4000-8000-000000000621", sender_role: "PARENT", sender_name: "Родитель Тестовый", body: "Сообщение родителя", created_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/teacher/communications/v2/threads/*/read", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ thread_id: thread.id, last_read_message_id: "00000000-0000-4000-8000-000000000618", last_read_at: "2026-09-30T10:00:00Z" }) }));
  await page.goto("/teacher/communications");
  await expect(page.getByRole("heading", { name: "Сообщения", level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: /Ребёнок Тестовый · Родитель Тестовый/ })).toBeVisible();
  await expect(page.getByText("Сообщение родителя")).toBeVisible();
  await expect(page.getByText("Родитель Тестовый", { exact: true })).toBeVisible();

  const announcement = { id: "00000000-0000-4000-8000-000000000625", target_type: "group", group_id: group.id, group_name: group.name, audience: "parents", title: "Напоминание", body: "Синтетический текст", status: "active", archived_at: null, published_at: "2026-09-30T10:00:00Z", unread: false, recipient_count: 1, can_manage: true };
  await page.route("**/api/v1/communications/v2/announcements?status=all", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement]) }));
  await page.goto("/teacher/announcements");
  await expect(page.getByText("Напоминание")).toBeVisible();
  await expect(page.getByText("Активно")).toBeVisible();
  await page.getByRole("button", { name: "Опубликовать для группы" }).click();
  await expect(page.getByText("Введите заголовок")).toBeVisible();
  await expect(page.getByText("Введите текст объявления")).toBeVisible();
});

test("direct URLs for deferred teacher modules return to teacher home", async ({ page }) => {
  for (const path of ["/teacher/diary", "/teacher/polls", "/teacher/incidents", "/teacher/photos"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/teacher$/);
  }
});

test("teacher empty assignment state remains usable", async ({ page }) => {
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [], schedule: [], attendance: [], tasks: [], notifications: [], unread_communication_count: 0 }) }));
  await page.goto("/teacher");
  await expect(page.getByText("0", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Мои группы", exact: true })).toBeVisible();
});
