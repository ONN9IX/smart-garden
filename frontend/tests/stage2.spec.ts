/** Stage 2 browser flow against the real API and disposable PostgreSQL. */
import { expect, test, type Page } from "@playwright/test";

async function login(page: Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Логин").fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
}

async function changePassword(page: Page, password: string) {
  await expect(page).toHaveURL(/\/change-password$/);
  await page.getByLabel("Новый пароль", { exact: true }).fill(password);
  await page.getByLabel("Повторите новый пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
}

test("director creates records; parent changes password and cannot manage them", async ({ page, browser }) => {
  const directorPassword = process.env.CI_STAGE2_DIRECTOR_PASSWORD;
  if (!directorPassword) throw new Error("CI_STAGE2_DIRECTOR_PASSWORD is required");
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  const suffix = crypto.randomUUID().slice(0, 8);
  const groupName = `Группа ${suffix}`;
  const childName = `Ребёнок${suffix}`;
  const guardianName = `Представитель${suffix}`;

  await login(page, "stage2-director-demo", directorPassword);
  await changePassword(page, `director-${crypto.randomUUID()}`);
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto("/groups");
  await page.getByLabel("Название группы").fill(groupName);
  await page.getByRole("button", { name: "Создать группу" }).click();
  await expect(page).toHaveURL(/\/groups\/[a-f0-9-]+$/);
  const groupUrl = page.url();
  await expect(page.getByRole("heading", { name: groupName })).toBeVisible();

  await page.setViewportSize({ width: 768, height: 900 });
  await page.goto("/children/new");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByLabel("Фамилия").fill("Тестовый");
  await page.getByLabel("Имя").fill(childName);
  await page.getByLabel("Дата рождения").fill("2020-01-01");
  await page.getByLabel("Группа", { exact: true }).selectOption({ label: groupName });
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page).toHaveURL(/\/children\/[a-f0-9-]+$/);
  const childUrl = page.url();
  await expect(page.getByRole("heading", { name: `Тестовый ${childName}` })).toBeVisible();
  await page.getByRole("link", { name: "Создать нового представителя и связать" }).click();
  await page.getByLabel("Фамилия").fill("Тестовый");
  await page.getByLabel("Имя").fill(guardianName);
  await page.getByLabel("Отношение к ребёнку").selectOption("mother");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page).toHaveURL(childUrl);
  await expect(page.getByRole("link", { name: `Тестовый ${guardianName}` })).toBeVisible();
  await page.getByRole("link", { name: `Тестовый ${guardianName}` }).click();
  await expect(page).toHaveURL(/\/guardians\/[a-f0-9-]+$/);
  const guardianUrl = page.url();

  await page.getByRole("button", { name: "Создать учётную запись родителя" }).click();
  const credentials = page.getByRole("status").filter({ hasText: "Временные данные для входа" });
  await expect(credentials).toBeVisible();
  const username = await credentials.getByText("Логин:").locator("strong").innerText();
  const temporary = await credentials.locator(".credential-value").innerText();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const cardBounds = await credentials.boundingBox();
  expect(cardBounds).not.toBeNull();
  expect(cardBounds!.x + cardBounds!.width).toBeLessThanOrEqual(390);
  await page.getByRole("button", { name: "Закрыть и скрыть пароль" }).click();
  await page.reload();
  await expect(page.locator(".credential-value")).toHaveCount(0);

  const parentContext = await browser.newContext({ baseURL: "http://localhost:3000" });
  const parentPage = await parentContext.newPage();
  parentPage.on("pageerror", (error) => pageErrors.push(error.message));
  try {
    await login(parentPage, username, temporary);
    const parentPassword = `parent-${crypto.randomUUID()}`;
    await changePassword(parentPage, parentPassword);
    await expect(parentPage).toHaveURL(/\/parent$/);
    await expect(parentPage.getByRole("heading", { name: "Кабинет родителя" })).toBeVisible();
    await parentPage.setViewportSize({ width: 390, height: 844 });
    expect(await parentPage.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await parentPage.goto("/children");
    await expect(parentPage).toHaveURL(/\/parent$/);
    expect((await parentPage.request.get("http://localhost:8000/api/v1/children")).status()).toBe(403);
    await parentPage.getByRole("button", { name: "Выйти" }).click();
    await expect(parentPage).toHaveURL(/\/login$/);
    await login(parentPage, username, parentPassword);
    await expect(parentPage).toHaveURL(/\/parent$/);

    await page.goto(groupUrl);
    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByRole("button", { name: "Архивировать" }).click();
    await expect(page.getByText("В группе есть активные дети. Сначала переведите или архивируйте их.")).toBeVisible();
    await page.goto(guardianUrl);
    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByRole("button", { name: "Архивировать" }).click();
    await expect(page.getByText("У представителя есть связи с активными детьми. Сначала уберите эти связи.")).toBeVisible();

    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByRole("button", { name: "Сбросить пароль" }).click();
    const resetCard = page.getByRole("status").filter({ hasText: "Временные данные для входа" });
    await expect(resetCard).toBeVisible();
    const resetPassword = await resetCard.locator(".credential-value").innerText();
    expect(resetPassword).not.toBe(temporary);
    expect((await parentPage.request.get("http://localhost:8000/api/v1/auth/me")).status()).toBe(401);
    expect((await parentPage.request.post("http://localhost:8000/api/v1/auth/login", {
      data: { username, password: parentPassword },
    })).status()).toBe(401);

    await page.goto(childUrl);
    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByRole("button", { name: "Архивировать" }).click();
    await expect(page.getByText("Карточка архивирована.")).toBeVisible();
    await page.goto(groupUrl);
    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByRole("button", { name: "Архивировать" }).click();
    await expect(page.getByText("Группа архивирована.")).toBeVisible();
    await page.goto(guardianUrl);
    page.once("dialog", (dialog) => void dialog.accept());
    await page.getByRole("button", { name: "Архивировать" }).click();
    await expect(page.getByText("Карточка архивирована.")).toBeVisible();
    await expect(page.getByText("Статус: Заблокирована")).toBeVisible();
    expect((await parentPage.request.post("http://localhost:8000/api/v1/auth/login", {
      data: { username, password: resetPassword },
    })).status()).toBe(403);
  } finally {
    await parentContext.close();
  }
  expect(pageErrors).toEqual([]);
});
