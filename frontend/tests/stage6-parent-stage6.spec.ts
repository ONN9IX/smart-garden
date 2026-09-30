/** Eligible PARENT Stage 6 read/action surfaces and no teacher writes. */
import { expect, test } from "@playwright/test";

const parent = { user: { id: "00000000-0000-4000-8000-000000000621", username: "parent-demo", role: "PARENT", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(parent) }));
  await page.route("**/api/v1/parent/announcements", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000622", target_type: "group", group_id: "00000000-0000-4000-8000-000000000611", title: "Объявление группы", body: "Синтетический текст", status: "active", created_by: "00000000-0000-4000-8000-000000000601", created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/parent/communications/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.route("**/api/v1/parent/polls", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000623", group_id: "00000000-0000-4000-8000-000000000611", question: "Придёте на праздник?", status: "active", closes_at: null, created_by: "00000000-0000-4000-8000-000000000601", created_at: "2026-09-30T10:00:00Z", selected_option_id: null, options: [{ id: "00000000-0000-4000-8000-000000000624", label: "Да", sort_order: 0 }] }]) }));
  await page.route("**/api/v1/parent/polls/*/vote", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{}" }));
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
