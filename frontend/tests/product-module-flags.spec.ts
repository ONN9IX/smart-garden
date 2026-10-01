/** Management navigation exposes only the current product baseline. */
import { expect, test } from "@playwright/test";

const director = {
  user: {
    id: "00000000-0000-4000-8000-000000000701",
    username: "director-demo",
    role: "DIRECTOR",
    status: "active",
    must_change_password: false,
  },
  organization: {
    id: "00000000-0000-4000-8000-000000000700",
    name: "Синтетический сад",
  },
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(director) }),
  );
  await page.route("**/api/v1/dashboard/summary", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: { code: "INTERNAL_ERROR", message: "Недоступно", field: null } }) }),
  );
  await page.route("**/api/v1/management/today", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: { code: "INTERNAL_ERROR", message: "Недоступно", field: null } }) }),
  );
});

test("management navigation hides deferred modules", async ({ page }) => {
  await page.goto("/dashboard");
  for (const label of ["Происшествия", "Опросы", "Дневник", "Уведомления о документах", "Согласия на фото"]) {
    await expect(page.getByRole("link", { name: label })).toHaveCount(0);
  }
  for (const label of ["Дети", "Группы", "Родители", "Посещаемость", "Расписание", "Объявления", "Задачи", "Сообщения", "Уведомления"]) {
    await expect(page.getByRole("link", { name: label })).toBeVisible();
  }
});

test("direct management URLs for deferred modules return to dashboard", async ({ page }) => {
  for (const path of ["/incidents", "/polls", "/diary", "/document-notices", "/photo-consents"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/dashboard$/);
  }
});
