/** Synthetic control-plane UI contracts; backend boundaries use PostgreSQL tests. */
import { expect, test, type Page } from "@playwright/test";

const id = "00000000-0000-4000-8000-000000000221";
const subscription = {
  status: "trial",
  plan_code: "standard",
  currency: "RUB",
  interval: "monthly",
  price_minor: 0,
  trial_ends_at: "2030-01-15T00:00:00Z",
  period_start: null,
  period_end: null,
};
const garden = {
  id,
  name: "Синтетический сад 221",
  timezone: "Europe/Moscow",
  status: "active",
  created_at: "2026-10-12T00:00:00Z",
  onboarding_status: "password_change_required",
  operating_profile: "KINDERGARTEN",
  subscription,
};
const identity = {
  username: "synthetic-owner",
  role: "PLATFORM_OWNER",
  csrf_token: "synthetic-csrf-only",
  credential_handoff_enabled: true,
  step_up_required: false,
};

async function mock(page: Page, authenticated = true) {
  const tenantRequests: string[] = [];
  page.on("request", (request) => {
    if (
      request.url().includes("/api/v1/") &&
      !request.url().includes("/api/v1/platform/")
    )
      tenantRequests.push(request.url());
  });
  await page.route("**/api/v1/platform/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = {};
    if (path.endsWith("/auth/me")) {
      if (!authenticated)
        return route.fulfill({
          status: 401,
          json: { error: { message: "Unauthorized" } },
        });
      body = identity;
    } else if (path.endsWith("/auth/login"))
      body = { mfa_required: true, csrf_token: identity.csrf_token };
    else if (path.endsWith("/mfa/verify")) {
      authenticated = true;
      body = identity;
    } else if (path.endsWith("/overview"))
      body = {
        organizations: { active: 1, blocked: 0, archived: 0 },
        subscriptions: { trial: 1 },
        pending_director_setup: 1,
      };
    else if (path.endsWith("/audit")) body = [];
    else if (path.endsWith(`/organizations/${id}`)) body = garden;
    else if (path.endsWith("/organizations")) body = [garden];
    await route.fulfill({ json: body });
  });
  return tenantRequests;
}

test("denied owner route and mandatory MFA without tenant session fetch", async ({
  page,
}) => {
  const tenantRequests = await mock(page, false);
  await page.goto("/platform/organizations");
  await expect(page).toHaveURL(/\/platform\/login$/);
  await page.getByLabel("Логин", { exact: true }).fill("synthetic-owner");
  await page
    .getByLabel("Пароль", { exact: true })
    .fill("synthetic-password-only");
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await expect(page.getByLabel("Код MFA", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/platform\/login$/);
  await page.getByLabel("Код MFA", { exact: true }).fill("123456");
  await page
    .getByRole("button", { name: "Подтвердить MFA", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Обзор организаций" }),
  ).toBeVisible();
  expect(tenantRequests).toEqual([]);
  expect(
    await page.evaluate(() => [localStorage.length, sessionStorage.length]),
  ).toEqual([0, 0]);
});

test("390px registry and explicit lifecycle confirmation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mock(page);
  await page.goto("/platform/organizations");
  await page.getByRole("link", { name: garden.name, exact: true }).click();
  const block = page.getByRole("button", {
    name: "Заблокировать сад",
    exact: true,
  });
  await expect(block).toBeDisabled();
  await page
    .getByLabel("Введите название сада для подтверждения")
    .fill("другой сад");
  await expect(block).toBeDisabled();
  await page
    .getByLabel("Введите название сада для подтверждения")
    .fill(garden.name);
  await expect(block).toBeEnabled();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("retry preserves idempotency key and never replays temporary password", async ({
  page,
}) => {
  await mock(page);
  const keys: string[] = [];
  await page.route("**/api/v1/platform/organizations", async (route) => {
    if (route.request().method() !== "POST") return route.fulfill({ json: [] });
    keys.push(route.request().postDataJSON().idempotency_key);
    if (keys.length === 1) return route.abort("failed");
    return route.fulfill({ json: { organization: garden, replayed: true } });
  });
  await page.goto("/platform/organizations/new");
  await page.getByLabel("Название сада", { exact: true }).fill(garden.name);
  await page
    .getByLabel("Логин первого директора")
    .fill("synthetic-director-221");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Создать сад", exact: true }).click();
  await expect(page.getByText("Нет соединения. Повторите запрос.", { exact: true })).toContainText("Нет соединения");
  await page.getByRole("button", { name: "Создать сад", exact: true }).click();
  await expect(
    page.getByText("Повтор запроса: пароль повторно не выдаётся."),
  ).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toEqual(keys[1]);
  await expect(page.getByLabel("Одноразовый пароль директора")).toHaveCount(0);
});
