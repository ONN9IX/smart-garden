import { expect, test, type Page } from "@playwright/test";

const requiredEnvironment = [
  "COMPAT_DIRECTOR_USERNAME",
  "COMPAT_DIRECTOR_PASSWORD",
  "COMPAT_ACTIVATION_USERNAME",
  "COMPAT_ACTIVATION_TOKEN",
  "COMPAT_ACTIVATION_PASSWORD",
  "COMPAT_RESET_USERNAME",
  "COMPAT_RESET_TOKEN",
  "COMPAT_RESET_PASSWORD",
  "COMPAT_GROUP_ID",
  "COMPAT_GROUP_NAME",
] as const;

function environment(name: typeof requiredEnvironment[number]): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for the real compatibility journey`);
  return value;
}

async function expectNoHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

async function login(page: Page, username: string, password: string, destination: RegExp) {
  await page.goto("/login");
  await page.getByLabel("Логин или email").fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(destination);
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

async function completePasswordLink(
  page: Page,
  path: "/activate" | "/reset-password",
  token: string,
  password: string,
) {
  await page.goto(`${path}#token=${token}`);
  await expect(page).toHaveURL(new RegExp(`${path}$`));
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  await page.getByLabel("Новый пароль", { exact: true }).fill(password);
  await page.getByLabel("Повторите новый пароль").fill(password);
  await page.getByRole("button", { name: "Сохранить пароль" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
}

test("real auth, recovery and protected group journey stays portable at 390px", async ({ page, browserName }) => {
  for (const name of requiredEnvironment) environment(name);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  await page.setViewportSize({ width: 390, height: 844 });

  await completePasswordLink(
    page,
    "/activate",
    environment("COMPAT_ACTIVATION_TOKEN"),
    environment("COMPAT_ACTIVATION_PASSWORD"),
  );
  await login(
    page,
    environment("COMPAT_ACTIVATION_USERNAME"),
    environment("COMPAT_ACTIVATION_PASSWORD"),
    /\/teacher$/,
  );
  await expectNoHorizontalOverflow(page);
  await logout(page);

  await completePasswordLink(
    page,
    "/reset-password",
    environment("COMPAT_RESET_TOKEN"),
    environment("COMPAT_RESET_PASSWORD"),
  );
  await login(
    page,
    environment("COMPAT_RESET_USERNAME"),
    environment("COMPAT_RESET_PASSWORD"),
    /\/dashboard$/,
  );
  await expectNoHorizontalOverflow(page);
  await logout(page);

  const generic = "Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email.";
  const requestRecovery = async (identifier: string) => {
    await page.goto("/forgot-password");
    await page.getByLabel("Логин или email").fill(identifier);
    const responsePromise = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/auth/forgot-password")
        && response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Отправить ссылку" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const payload = await response.json() as { message: string };
    await expect(page.getByText(generic, { exact: true })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    return payload.message;
  };
  const existingMessage = await requestRecovery(environment("COMPAT_RESET_USERNAME"));
  const missingMessage = await requestRecovery("missing-compatibility@example.test");
  expect(existingMessage).toBe(generic);
  expect(missingMessage).toBe(existingMessage);

  await login(
    page,
    environment("COMPAT_DIRECTOR_USERNAME"),
    environment("COMPAT_DIRECTOR_PASSWORD"),
    /\/dashboard$/,
  );
  await page.goto(`/groups/${environment("COMPAT_GROUP_ID")}`);
  await expect(page.getByRole("heading", { name: environment("COMPAT_GROUP_NAME") })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Дети" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  await logout(page);

  expect(errors, `${browserName} emitted runtime errors`).toEqual([]);
});
