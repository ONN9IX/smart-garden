/** Stage 3 browser path uses disposable PostgreSQL and synthetic credentials. */
import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Логин").fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
}
async function rotate(page: Page) {
  await expect(page).toHaveURL(/\/change-password$/);
  const password = `stage3-${crypto.randomUUID()}`;
  await page.getByLabel("Новый пароль", { exact: true }).fill(password);
  await page.getByLabel("Повторите новый пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("employee ADMIN lifecycle and manual attendance", async ({ page, browser }) => {
  const password = process.env.CI_STAGE3_DIRECTOR_PASSWORD;
  if (!password) throw new Error("CI_STAGE3_DIRECTOR_PASSWORD is required");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await login(page, "stage3-director-demo", password);
  await rotate(page);
  await page.goto("/employees/new");
  await page.getByLabel("Фамилия").fill("Тестовая");
  await page.getByLabel("Имя").fill("Сотрудница");
  await page.getByLabel("Должность").fill("Администратор");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page).toHaveURL(/\/employees\/[a-f0-9-]+$/);
  const employeeUrl = page.url();
  await page.getByRole("button", { name: "Выдать доступ администратора" }).click();
  const credentials = page.getByRole("region", { name: "Одноразовые реквизиты" });
  await expect(credentials).toBeVisible();
  const username = await credentials.getByText("Логин:").locator("strong").innerText();
  const temporary = await credentials.getByText("Временный пароль:").locator("strong").innerText();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Закрыть и скрыть пароль" }).click();
  await page.reload();
  await expect(page.getByRole("region", { name: "Одноразовые реквизиты" })).toHaveCount(0);

  const staff = await browser.newContext({ baseURL: "http://localhost:3000" });
  const staffPage = await staff.newPage();
  try {
    await login(staffPage, username, temporary);
    await rotate(staffPage);
    await staffPage.goto(employeeUrl);
    await expect(staffPage.getByRole("button", { name: "Сбросить пароль" })).toHaveCount(0);
    expect((await staffPage.request.post(`http://localhost:8000/api/v1/employees/${employeeUrl.split("/").pop()}/account/block`)).status()).toBe(403);
    await page.goto(employeeUrl);
    await page.getByRole("button", { name: "Заблокировать" }).click();
    await expect(page.getByText("Доступ заблокирован.")).toBeVisible();
    expect((await staffPage.request.get("http://localhost:8000/api/v1/auth/me")).status()).toBe(401);
  } finally { await staff.close(); }

  await page.goto("/groups");
  const group = `Группа ${crypto.randomUUID().slice(0, 8)}`;
  await page.getByLabel("Название группы").fill(group);
  await page.getByRole("button", { name: "Создать группу" }).click();
  await page.goto("/children/new");
  await page.getByLabel("Фамилия").fill("Тестовый");
  await page.getByLabel("Имя").fill("Ребёнок");
  await page.getByLabel("Дата рождения").fill("2020-01-01");
  await page.getByLabel("Группа", { exact: true }).selectOption({ label: group });
  await page.getByRole("button", { name: "Сохранить" }).click();
  await page.goto("/attendance");
  const row = page.locator(".attendance-list form").filter({ hasText: "Тестовый Ребёнок" });
  await expect(row).toContainText("Без отметки");
  await row.getByLabel("Отметка").selectOption("present");
  await row.getByLabel("Приход").fill("08:30");
  await row.getByRole("button", { name: "Сохранить отметку" }).click();
  await expect(row).toContainText("Присутствует");
  await row.getByLabel("Отметка").selectOption("absent");
  await row.getByRole("button", { name: "Сохранить отметку" }).click();
  await expect(row).toContainText("Отсутствует");
  await page.setViewportSize({ width: 768, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
