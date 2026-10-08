import { expect, test, type Route } from "@playwright/test";

const groupA = "11111111-1111-4111-8111-111111111111";
const groupB = "22222222-2222-4222-8222-222222222222";
const scheduleId = "33333333-3333-4333-8333-333333333333";
const auth = {
  user: { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", username: "director-synthetic", role: "DIRECTOR", status: "active", must_change_password: false },
  organization: { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name: "Синтетический сад" },
};
const groups = { items: [
  { id: groupA, name: "Ромашка", status: "active", archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  { id: groupB, name: "Солнышко", status: "active", archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
] };

const reply = (route: Route, body: object, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

test("DIRECTOR group card has no OFF Incidents or Polls entry points", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => reply(route, auth));
  await page.route(`**/api/v1/groups/${groupA}`, (route) => reply(route, groups.items[0]));
  await page.route("**/api/v1/children?**", (route) => reply(route, { items: [] }));
  await page.goto(`/groups/${groupA}`);
  await expect(page.getByRole("link", { name: "Расписание" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Происшествия" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Опросы" })).toHaveCount(0);
});

test("Schedule edit submits group, day, both times and title with local validation", async ({ page }) => {
  let schedule = { items: [{ id: scheduleId, group_id: groupA, group_name: "Ромашка", weekday: 0, start_time: "09:00:00", end_time: "10:00:00", title: "Музыка", status: "active" }] };
  await page.route("**/api/v1/auth/me", (route) => reply(route, auth));
  await page.route("**/api/v1/groups?**", (route) => reply(route, groups));
  await page.route("**/api/v1/teacher-management/schedule?**", (route) => reply(route, schedule));
  await page.route(`**/api/v1/teacher-management/schedule/${scheduleId}`, async (route) => {
    const data = route.request().postDataJSON();
    schedule = { items: [{ ...schedule.items[0], ...data, group_name: "Солнышко", start_time: `${data.start_time}:00`, end_time: `${data.end_time}:00` }] };
    return reply(route, schedule.items[0]);
  });
  await page.goto("/schedule");
  await page.getByRole("button", { name: "Изменить" }).click();
  await page.getByLabel("Группа события").selectOption(groupB);
  await page.getByLabel("День события").selectOption("2");
  await page.getByLabel("Начало события").fill("11:00");
  await page.getByLabel("Окончание события").fill("10:00");
  await page.getByLabel("Название события").fill("Ритмика");
  await page.getByRole("button", { name: "Сохранить" }).last().click();
  await expect(page.getByText("Время окончания должно быть позже времени начала.")).toBeVisible();
  await page.getByLabel("Окончание события").fill("12:00");
  const request = page.waitForRequest(`**/api/v1/teacher-management/schedule/${scheduleId}`);
  await page.getByRole("button", { name: "Сохранить" }).last().click();
  expect((await request).postDataJSON()).toEqual({ group_id: groupB, weekday: 2, start_time: "11:00", end_time: "12:00", title: "Ритмика" });
  await expect(page.getByText("Ср · 11:00–12:00 · Ритмика")).toBeVisible();
});

test("Announcement create reuses one idempotency key across a retry", async ({ page }) => {
  const keys: string[] = [];
  let attempts = 0;
  await page.route("**/api/v1/auth/me", (route) => reply(route, auth));
  await page.route("**/api/v1/groups?**", (route) => reply(route, groups));
  await page.route("**/api/v1/communications/v2/announcements", (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    attempts += 1;
    if (attempts === 1) return route.abort("failed");
    return reply(route, { id: scheduleId, target_type: "all", group_id: null, group_name: null, audience: "all", title: "Важно", body: "Синтетический текст", status: "active", archived_at: null, published_at: "2026-10-07T10:00:00Z", unread: false, recipient_count: 3, can_manage: true }, 201);
  });
  await page.goto("/announcements/new");
  await page.getByLabel("Заголовок").fill("Важно");
  await page.getByLabel("Текст").fill("Синтетический текст");
  await page.getByRole("button", { name: "Опубликовать" }).click();
  await expect(page.getByText(/Нет соединения/)).toBeVisible();
  await page.getByRole("button", { name: "Опубликовать" }).click();
  await expect(page).toHaveURL(new RegExp(`/announcements/${scheduleId}$`));
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBeTruthy();
  expect(keys[1]).toBe(keys[0]);
});
