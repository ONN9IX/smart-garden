/** PARENT cabinet keeps announcements and communications while deferred modules stay hidden. */
import { expect, test } from "@playwright/test";

const parent = { user: { id: "00000000-0000-4000-8000-000000000621", username: "parent-demo", role: "PARENT", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };
const child = { id: "00000000-0000-4000-8000-000000000612", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null };
const groupId = "00000000-0000-4000-8000-000000000611";
const thread = { id: "00000000-0000-4000-8000-000000000625", thread_type: "direct", group_id: groupId, audience: "all", child_id: child.id, guardian_id: "00000000-0000-4000-8000-000000000626", created_at: "2026-09-30T09:00:00Z" };
let threads: typeof thread[] = [];

test.beforeEach(async ({ page }) => {
  threads = [];
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(parent) }));
  await page.route("**/api/v1/parent/children", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child]) }));
  await page.route(`**/api/v1/parent/children/${child.id}/today`, (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      date: "2026-09-30",
      child,
      group: { id: groupId, name: "Ромашка" },
      attendance: { status: "present", arrival_time: "08:15:00", departure_time: null },
      schedule: [{ id: "00000000-0000-4000-8000-000000000629", group_id: groupId, weekday: 2, start_time: "09:00:00", end_time: "09:30:00", title: "Музыка" }],
    }),
  }));
  await page.route("**/api/v1/parent/announcements", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000622", target_type: "group", group_id: groupId, title: "Объявление группы", body: "Синтетический текст", status: "active", created_by: "00000000-0000-4000-8000-000000000601", created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/parent/communications/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(threads) }));
  await page.route("**/api/v1/parent/communications/direct", async (route) => {
    threads = [thread];
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(thread) });
  });
  await page.route("**/api/v1/parent/communications/threads/*/messages", (route) => route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, contentType: "application/json", body: route.request().method() === "POST" ? JSON.stringify({ id: "00000000-0000-4000-8000-000000000627", thread_id: thread.id, sender_user_id: parent.user.id, sender_role: "PARENT", sender_name: "Родитель Тестовый", body: "Ответ родителя", created_at: "2026-09-30T10:05:00Z" }) : JSON.stringify([{ id: "00000000-0000-4000-8000-000000000628", thread_id: thread.id, sender_user_id: "00000000-0000-4000-8000-000000000601", sender_role: "TEACHER", sender_name: "Воспитатель Тестовый", body: "Сообщение воспитателя", created_at: "2026-09-30T10:00:00Z" }]) }));
});

test("parent sees daily child overview and only enabled modules", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/parent");
  await expect(page.getByRole("heading", { name: "Кабинет родителя" })).toBeVisible();
  await expect(page.locator(".auth-brand")).toContainText("ПРОМАКС");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole("button", { name: "Сегодня" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("heading", { name: "Группа Ромашка" })).toBeVisible();
  await expect(page.getByText("Ежедневная информация")).toBeVisible();
  await expect(page.getByText("В детском саду")).toBeVisible();
  await expect(page.getByText("Приход: 08:15")).toBeVisible();
  await expect(page.getByText("Музыка")).toBeVisible();
  for (const label of ["Дневник", "Опросы", "Фото"]) {
    await expect(page.getByRole("button", { name: label })).toHaveCount(0);
  }
  await page.getByRole("button", { name: "Объявления" }).click();
  await expect(page.getByText("Объявление группы")).toBeVisible();
  await expect(page.getByRole("button", { name: "Сообщения" })).toBeVisible();
});

test("parent bootstraps direct chat from linked child", async ({ page }) => {
  await page.goto("/parent");
  await page.getByRole("button", { name: "Сообщения" }).click();
  await expect(page.getByLabel("Ребёнок")).toHaveValue(child.id);
  await expect(page.getByRole("button", { name: "Отправить" })).toBeDisabled();
  await page.getByRole("button", { name: "Открыть личный диалог" }).click();
  await expect(page.getByRole("button", { name: "Воспитатель · Ребёнок Тестовый" })).toBeVisible();
  await expect(page.getByText("Сообщение воспитателя")).toBeVisible();
  await expect(page.getByText("Воспитатель Тестовый")).toBeVisible();
  await page.getByLabel("Ответ").fill("Ответ родителя");
  await page.getByRole("button", { name: "Отправить" }).click();
});
