/** QA3-03 targeted restore-confirmation regression with synthetic responses. */
import { expect, test, type Page, type Route } from "@playwright/test";

const employeeId = "11111111-1111-4111-8111-111111111111";
const account = { id: "66666666-6666-4666-8666-666666666666", username: "staff-synthetic", role: "ADMIN", status: "blocked", must_change_password: false };
const archived = {
  id: employeeId, first_name: "Тест", last_name: "Синтетический", middle_name: null,
  position: "Сотрудник", status: "archived", account, archived_at: "2026-01-02T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-02T00:00:00Z",
};
const cors = {
  "access-control-allow-origin": "http://localhost:3000", "access-control-allow-credentials": "true",
  "access-control-allow-methods": "GET,POST,PATCH,OPTIONS", "access-control-allow-headers": "content-type",
};
const reply = (route: Route, body: object, status = 200) => route.fulfill({
  status, contentType: "application/json", headers: cors, body: JSON.stringify(body),
});

async function mockAuth(page: Page) {
  await page.route("**/api/v1/auth/me", (route) => reply(route, {
    user: { id: "77777777-7777-4777-8777-777777777777", username: "director-synthetic", role: "DIRECTOR", status: "active", must_change_password: false },
    organization: { id: "88888888-8888-4888-8888-888888888888", name: "Синтетический сад" },
  }));
}

test("employee restore requires explicit confirmation and cancel sends no request", async ({ page }) => {
  await mockAuth(page);
  let restorePosts = 0;
  await page.route("**/api/v1/employees/**", (route) => {
    const { pathname } = new URL(route.request().url());
    if (route.request().method() === "GET") return reply(route, archived);
    if (route.request().method() === "POST" && pathname.endsWith("/restore")) {
      restorePosts += 1;
      return reply(route, { ...archived, status: "active", archived_at: null });
    }
    return reply(route, { error: { code: "INTERNAL_ERROR", message: "Hidden server details", field: null } }, 500);
  });

  await page.goto(`/employees/${employeeId}`);
  page.once("dialog", async (dialog) => {
    expect(dialog.message()).toContain("не разблокирует связанного User автоматически");
    await dialog.dismiss();
  });
  await page.getByRole("button", { name: "Восстановить" }).click();
  await expect(page.getByRole("button", { name: "Восстановить" })).toBeVisible();
  expect(restorePosts).toBe(0);

  page.once("dialog", async (dialog) => {
    expect(dialog.message()).toContain("не разблокирует связанного User автоматически");
    await dialog.accept();
  });
  await page.getByRole("button", { name: "Восстановить" }).click();
  await expect(page.getByText("Карточка восстановлена. Доступ остаётся заблокированным, если был выдан.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Разблокировать" })).toBeVisible();
  expect(restorePosts).toBe(1);
});
