/** Stage 1 browser flow across Next.js, FastAPI, and PostgreSQL. Synthetic users only. */
import { expect, test } from "@playwright/test";

const directorPassword = process.env.CI_DIRECTOR_PASSWORD;
const adminPassword = process.env.CI_ADMIN_PASSWORD;

test("temporary DIRECTOR password, protected routes, rotation, refresh and logout", async ({ page }) => {
  if (!directorPassword) throw new Error("CI_DIRECTOR_PASSWORD is required");
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Логин").fill("director-demo");
  await page.getByLabel("Пароль", { exact: true }).fill(directorPassword);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(/\/change-password$/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/change-password$/);
  const newPassword = `new-secret-${crypto.randomUUID()}`;
  await page.getByLabel("Новый пароль").fill(newPassword);
  await page.getByLabel("Повторите новый пароль").fill(newPassword);
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("main")).toContainText("Директор");
  await expect(page.getByRole("main")).toContainText("Детский сад «Солнышко»");
  await page.reload();
  await expect(page.getByRole("main")).toContainText("director-demo");
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Логин").fill("director-demo");
  await page.getByLabel("Пароль", { exact: true }).fill(directorPassword);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("alert")).toContainText("Неверный логин или пароль");
});

test("ADMIN role comes from the backend", async ({ page }) => {
  if (!adminPassword) throw new Error("CI_ADMIN_PASSWORD is required");
  await page.goto("/login");
  await page.getByLabel("Логин").fill("admin-demo");
  await page.getByLabel("Пароль", { exact: true }).fill(adminPassword);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(/\/change-password$/);
  const newPassword = `new-secret-${crypto.randomUUID()}`;
  await page.getByLabel("Новый пароль").fill(newPassword);
  await page.getByLabel("Повторите новый пароль").fill(newPassword);
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("main")).toContainText("Администратор");
});
