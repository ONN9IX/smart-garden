/** Eligible PARENT Stage 6 read/action surfaces and linked-child bootstrap. */
import { expect, test } from "@playwright/test";

const parent = { user: { id: "00000000-0000-4000-8000-000000000621", username: "parent-demo", role: "PARENT", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };
const child = { id: "00000000-0000-4000-8000-000000000612", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null };
const groupId = "00000000-0000-4000-8000-000000000611";
const thread = { id: "00000000-0000-4000-8000-000000000625", thread_type: "direct", group_id: groupId, child_id: child.id, guardian_id: "00000000-0000-4000-8000-000000000626", created_at: "2026-09-30T09:00:00Z" };
let threads: typeof thread[] = [];

test.beforeEach(async ({ page }) => {
  threads = [];
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(parent) }));
  await page.route("**/api/v1/parent/children", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child]) }));
  await page.route("**/api/v1/parent/announcements", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000622", target_type: "group", group_id: groupId, title: "Объявление группы", body: "Синтетический текст", status: "active", created_by: "00000000-0000-4000-8000-000000000601", created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/parent/communications/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(threads) }));
  await page.route("**/api/v1/parent/communications/direct", async (route) => {
    threads = [thread];
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(thread) });
  });
  await page.route("**/api/v1/parent/communications/threads/*/messages", (route) => route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, contentType: "application/json", body: route.request().method() === "POST" ? JSON.stringify({ id: "00000000-0000-4000-8000-000000000627", thread_id: thread.id, sender_user_id: parent.user.id, body: "Ответ родителя", created_at: "2026-09-30T10:05:00Z" }) : JSON.stringify([{ id: "00000000-0000-4000-8000-000000000628", thread_id: thread.id, sender_user_id: "00000000-0000-4000-8000-000000000601", body: "Сообщение воспитателя", created_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route(`**/api/v1/parent/children/${child.id}/diary`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000629", child_id: child.id, group_id: groupId, date: "2026-09-30", author_user_id: "00000000-0000-4000-8000-000000000601", note: "Хороший день", created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/parent/polls", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000623", group_id: groupId, question: "Придёте на праздник?", status: "active", closes_at: null, created_by: "00000000-0000-4000-8000-000000000601", created_at: "2026-09-30T10:00:00Z", selected_option_id: null, options: [{ id: "00000000-0000-4000-8000-000000000624", label: "Да", sort_order: 0 }] }]) }));
  await page.route("**/api/v1/parent/polls/*/vote", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
  await page.route("**/api/v1/parent/photos?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000630", group_id: groupId, child_ids: [child.id], mime_type: "image/png", size_bytes: 16, captured_at: null, status: "active", created_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/parent/photos/*/content", (route) => route.fulfill({ status: 200, contentType: "image/png", body: Buffer.from("synthetic") }));
});

test("parent reads eligible announcements and votes once through the cabinet", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/parent");
  await expect(page.getByRole("heading", { name: "Кабинет родителя" })).toBeVisible();
  await expect(page.getByText("Объявление группы")).toBeVisible();
  await page.getByRole("button", { name: "Опросы" }).click();
  await expect(page.getByText("Придёте на праздник?")).toBeVisible();
  await page.getByRole("button", { name: "Да" }).click();
  await expect(page.getByRole("link", { name: "Сотрудники" })).toHaveCount(0);
  await expect(page.getByText("Родительский кабинет пока недоступен")).toHaveCount(0);
});

test("parent bootstraps direct chat from linked child and uses diary and photos", async ({ page }) => {
  await page.goto("/parent");
  await page.getByRole("button", { name: "Сообщения" }).click();
  await expect(page.getByLabel("Ребёнок")).toHaveValue(child.id);
  await expect(page.getByRole("button", { name: "Отправить" })).toBeDisabled();
  await page.getByRole("button", { name: "Открыть личный диалог" }).click();
  await expect(page.getByRole("button", { name: "Воспитатель" })).toBeVisible();
  await expect(page.getByText("Сообщение воспитателя")).toBeVisible();
  await page.getByLabel("Ответ").fill("Ответ родителя");
  await page.getByRole("button", { name: "Отправить" }).click();

  await page.getByRole("button", { name: "Дневник" }).click();
  await expect(page.getByRole("combobox")).toContainText("Ребёнок Тестовый");
  await expect(page.getByText("Хороший день")).toBeVisible();

  await page.getByRole("button", { name: "Фото" }).click();
  await expect(page.getByRole("combobox")).toContainText("Ребёнок Тестовый");
  await expect(page.getByAltText("Фото группы")).toBeVisible();
});
