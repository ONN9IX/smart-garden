/** Stage 4 Audit: real Browser -> Next.js -> FastAPI -> PostgreSQL coverage. */
import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const apiBase = "http://localhost:8000/api/v1";
test.setTimeout(120_000);

async function login(page: Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Логин").fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
}

async function rotate(page: Page, prefix: string, destination = /\/dashboard$/) {
  await expect(page).toHaveURL(/\/change-password$/);
  const password = `${prefix}-${crypto.randomUUID()}`;
  await page.getByLabel("Новый пароль", { exact: true }).fill(password);
  await page.getByLabel("Повторите новый пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
  await expect(page).toHaveURL(destination);
}

async function createAccount(
  context: BrowserContext,
  kind: "employee" | "guardian",
  suffix: string,
) {
  const collection = kind === "employee" ? "employees" : "guardians";
  const fields = kind === "employee"
    ? { first_name: "Аудит", last_name: `Сотрудник${suffix}`, middle_name: null, position: "Администратор" }
    : { first_name: "Аудит", last_name: `Родитель${suffix}`, middle_name: null, phone: null, email: null };
  const recordResponse = await context.request.post(`${apiBase}/${collection}`, { data: fields });
  expect(recordResponse.status()).toBe(201);
  const record = await recordResponse.json() as { id: string };
  const credentialsResponse = await context.request.post(`${apiBase}/${collection}/${record.id}/account`);
  expect(credentialsResponse.status()).toBe(201);
  return await credentialsResponse.json() as { account: { username: string }; temporary_password: string };
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("immutable Audit UI, RBAC, privacy and tenant isolation", async ({ page, browser }) => {
  const directorPassword = process.env.CI_STAGE4_DIRECTOR_PASSWORD;
  const otherPassword = process.env.CI_STAGE4_OTHER_DIRECTOR_PASSWORD;
  if (!directorPassword || !otherPassword) throw new Error("Stage 4 synthetic passwords are required");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const suffix = crypto.randomUUID().slice(0, 8);
  const groupName = `Аудит группа ${suffix}`;

  await login(page, "stage4-director-demo", directorPassword);
  await rotate(page, "director-stage4");
  await expect(page.getByRole("link", { name: "Аудит" })).toBeVisible();
  await page.goto("/groups");
  await page.getByLabel("Название группы").fill(groupName);
  await page.getByRole("button", { name: "Создать группу" }).click();
  await expect(page).toHaveURL(/\/groups\/[a-f0-9-]+$/);

  const director = page.context();
  const adminCredentials = await createAccount(director, "employee", suffix);
  const parentCredentials = await createAccount(director, "guardian", suffix);

  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Журнал аудита" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "group.create", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "account.create", exact: true }).first()).toBeVisible();
  const auditText = await page.locator("main").innerText();
  expect(auditText).not.toContain(groupName);
  expect(auditText).not.toContain(`Сотрудник${suffix}`);
  expect(auditText).not.toContain(`Родитель${suffix}`);
  expect(auditText).not.toContain(adminCredentials.temporary_password);
  expect(auditText).not.toContain(parentCredentials.temporary_password);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  for (const viewport of [{ width: 1280, height: 900 }, { width: 768, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await noOverflow(page);
  }

  const ownAudit = await director.request.get(`${apiBase}/audit?limit=1`);
  expect(ownAudit.status()).toBe(200);
  const ownAuditId = (await ownAudit.json() as { items: Array<{ id: string }> }).items[0].id;

  const admin = await browser.newContext({ baseURL: "http://localhost:3000" });
  const adminPage = await admin.newPage();
  adminPage.on("pageerror", (error) => errors.push(error.message));
  await login(adminPage, adminCredentials.account.username, adminCredentials.temporary_password);
  await rotate(adminPage, "admin-stage4");
  await expect(adminPage.getByRole("link", { name: "Аудит" })).toHaveCount(0);
  await adminPage.goto("/audit");
  await expect(adminPage).toHaveURL(/\/403$/);
  expect((await adminPage.request.get(`${apiBase}/audit`)).status()).toBe(403);
  await admin.close();

  const parent = await browser.newContext({ baseURL: "http://localhost:3000" });
  const parentPage = await parent.newPage();
  parentPage.on("pageerror", (error) => errors.push(error.message));
  await login(parentPage, parentCredentials.account.username, parentCredentials.temporary_password);
  await rotate(parentPage, "parent-stage4", /\/parent$/);
  await parentPage.goto("/audit");
  await expect(parentPage).toHaveURL(/\/parent$/);
  expect((await parentPage.request.get(`${apiBase}/audit`)).status()).toBe(403);
  await parent.close();

  const other = await browser.newContext({ baseURL: "http://localhost:3000" });
  const otherPage = await other.newPage();
  otherPage.on("pageerror", (error) => errors.push(error.message));
  await login(otherPage, "stage4-other-director-demo", otherPassword);
  await rotate(otherPage, "other-director-stage4");
  const foreignGroup = await otherPage.request.post(`${apiBase}/groups`, { data: { name: `Чужая аудит группа ${suffix}` } });
  expect(foreignGroup.status()).toBe(201);
  const foreignAudit = await otherPage.request.get(`${apiBase}/audit?limit=1`);
  const foreignAuditId = (await foreignAudit.json() as { items: Array<{ id: string }> }).items[0].id;
  expect(foreignAuditId).not.toBe(ownAuditId);
  expect((await director.request.get(`${apiBase}/audit/${foreignAuditId}`)).status()).toBe(404);
  await other.close();

  expect(errors).toEqual([]);
});
