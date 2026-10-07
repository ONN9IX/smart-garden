import { expect, test } from "@playwright/test";

const auth = { user: { id: "u1", username: "director", role: "DIRECTOR", status: "active", must_change_password: false }, organization: { id: "o1", name: "Сад" } };

test("login accepts login or email and forgot response stays generic", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { code: "UNAUTHORIZED", message: "", field: null } }) }));
  await page.route("**/api/v1/auth/forgot-password", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: "Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email." }) }));
  await page.goto("/login");
  await expect(page.getByLabel("Логин или email")).toBeVisible();
  await page.getByRole("link", { name: "Забыли пароль?" }).click();
  await page.getByLabel("Логин или email").fill("unknown@example.test");
  await page.getByRole("button", { name: "Отправить ссылку" }).click();
  await expect(page.getByText("Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email.")).toBeVisible();
});

for (const [path, heading, endpoint] of [
  ["/activate", "Активировать доступ", "/auth/activate"],
  ["/reset-password", "Новый пароль", "/auth/reset-password"],
] as const) {
  test(`${path} removes token fragment and never persists it`, async ({ page }) => {
    let body = "";
    await page.route(`**/api/v1${endpoint}`, async (route) => { body = route.request().postData() ?? ""; await route.fulfill({ status: 200, contentType: "application/json", body: '{"success":true}' }); });
    await page.goto(`${path}#token=secret-token-value-with-more-than-32-characters`);
    await expect(page).toHaveURL(new RegExp(`${path}$`));
    expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await page.getByLabel("Новый пароль").fill("safe-browser-password-123");
    await page.getByRole("button", { name: "Сохранить пароль" }).click();
    expect(body).toContain("secret-token-value");
    expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  });
}

test("Access & Accounts renders statuses and has no plaintext password at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(auth) }));
  await page.route("**/api/v1/access-accounts", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
    parents: [{ profile_id: "g1", profile_type: "guardian", full_name: "Иванова Анна", context: "Родитель", username: "parent-one", role: "PARENT", masked_email: "a***@example.test", status: "invited", last_login_at: null, groups: [] }],
    teachers: [], administrators: [], other_employees: [], blocked: [],
  }) }));
  await page.goto("/access-accounts");
  await expect(page.getByRole("heading", { name: "Доступ и аккаунты" })).toBeVisible();
  await expect(page.getByText("Приглашение отправлено", { exact: true })).toBeVisible();
  await expect(page.getByText(/временный пароль/i)).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
