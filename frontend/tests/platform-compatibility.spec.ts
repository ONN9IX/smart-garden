import { expect, test, type Page } from "@playwright/test";

function runtimeErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  return errors;
}

test("critical login/recovery and management shell stay portable at 390px", async ({ page, browserName }) => {
  const errors = runtimeErrors(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { code: "UNAUTHORIZED", message: "", field: null } }) }));
  await page.route("**/api/v1/auth/forgot-password", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: "Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email." }) }));
  await page.goto("/login");
  await expect(page.getByLabel("Логин или email")).toBeVisible();
  await page.getByRole("link", { name: "Забыли пароль?" }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await expect(page.getByRole("heading", { name: "Восстановление доступа" })).toBeVisible();
  await page.getByLabel("Логин или email").fill("synthetic@example.test");
  await page.getByRole("button", { name: "Отправить ссылку" }).click();
  await expect(page.getByText(/Если аккаунт найден/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await page.unroute("**/api/v1/auth/me");
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ user: { id: "u1", username: "director-synthetic", role: "DIRECTOR", status: "active", must_change_password: false }, organization: { id: "o1", name: "Синтетический сад" } }) }));
  await page.route("**/api/v1/access-accounts", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ parents: [], teachers: [], administrators: [], other_employees: [], blocked: [] }) }));
  await page.goto("/access-accounts");
  await expect(page.getByRole("heading", { name: "Доступ и аккаунты" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors, `${browserName} emitted runtime errors`).toEqual([]);
});
