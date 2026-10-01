/** Stage 6 Foundation shared auth routing and minimal TEACHER shell. */
import { expect, test } from "@playwright/test";

const teacherContext = {
  user: {
    id: "00000000-0000-0000-0000-000000000601",
    username: "stage6-teacher-demo",
    role: "TEACHER",
    status: "active",
    must_change_password: false,
  },
  organization: { id: "00000000-0000-0000-0000-000000000600", name: "Синтетический детский сад" },
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify(teacherContext),
  }));
});

test("TEACHER is routed to an isolated minimal cabinet shell", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/teacher$/);
  await expect(page.getByRole("heading", { name: "Кабинет воспитателя" })).toBeVisible();
  await expect(page.getByText("Воспитатель", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Сегодня" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Дети" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Группы", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Сотрудники" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Аудит" })).toHaveCount(0);
});

test("TEACHER cannot stay on a management route", async ({ page }) => {
  await page.goto("/employees");
  await expect(page).toHaveURL(/\/teacher$/);
  await expect(page.getByRole("heading", { name: "Кабинет воспитателя" })).toBeVisible();
});
