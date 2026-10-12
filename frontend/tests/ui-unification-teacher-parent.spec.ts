/** Synthetic API fixtures exercise rendered role UI, never production accounts. */
import { expect, test, type Page } from "@playwright/test";

const group = { id: "11111111-1111-4111-8111-111111111111", name: "Ромашка" };
const groupB = { id: "11111111-1111-4111-8111-111111111112", name: "Солнышко" };
const child = { id: "22222222-2222-4222-8222-222222222222", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null, status: "active" };
const childB = { ...child, id: "22222222-2222-4222-8222-222222222223", first_name: "Второй" };
const thread = { id: "33333333-3333-4333-8333-333333333333", thread_type: "direct", group_id: group.id, group_name: group.name, audience: "all", child_id: child.id, child_name: "Ребёнок Тестовый", guardian_id: "guardian", teacher_employee_id: "teacher", teacher_name: "Воспитатель Тестовый", preview: null, unread_count: 0 };
const today = { date: "2026-10-12", child, group, attendance: { status: "present", arrival_time: "08:15:00", departure_time: null }, schedule: [{ id: "lesson", group_id: group.id, weekday: 0, start_time: "09:00:00", end_time: "09:30:00", title: "Музыка" }] };
const teacherToday = { date: today.date, groups: [group, groupB], attendance: [{ group_id: group.id, active_children: 8, present: 4, on_site: 2, departed: 1, absent: 1, unknown: 3, needs_arrival: 1 }], schedule: [], tasks: [], notifications: [], unread_communication_count: 1 };

async function fixtures(page: Page, role: "TEACHER" | "PARENT") {
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204 });
    let json: unknown = [];
    if (path.endsWith("/auth/me")) json = { user: { id: "synthetic-user", username: `${role.toLowerCase()}-demo`, role, status: "active", must_change_password: false }, organization: { id: "synthetic-garden", name: "Синтетический сад" } };
    else if (path.endsWith("/teacher/today")) json = teacherToday;
    else if (path.endsWith("/teacher/groups")) json = [group, groupB];
    else if (path.endsWith("/parent/children")) json = [child, childB];
    else if (path.endsWith("/today")) json = path.includes(childB.id) ? { ...today, child: childB, group: groupB, attendance: { status: "absent", arrival_time: null, departure_time: null } } : today;
    else if (path.endsWith("/teacher/attendance")) json = [{ record_id: null, date: today.date, child, group, status: "unknown", arrival_time: null, departure_time: null }];
    else if (path.endsWith("/threads")) json = [thread];
    else if (path.endsWith("/messages")) json = [{ id: "message", thread_id: thread.id, sender_user_id: "teacher", sender_role: "TEACHER", sender_name: "Воспитатель Тестовый", body: "Синтетическое сообщение", created_at: "2026-10-12T10:00:00Z" }];
    else if (path.endsWith("/read")) json = {};
    else if (path.endsWith("/teachers")) json = [{ employee_id: "teacher", display_name: "Воспитатель Тестовый", group_id: group.id, group_name: group.name }];
    return route.fulfill({ json });
  });
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

for (const width of [390, 768, 1440]) {
  test(`teacher attendance priority and role navigation at ${width}px`, async ({ page }) => {
    await fixtures(page, "TEACHER");
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/teacher");
    const action = page.getByRole("link", { name: "Отметить посещаемость", exact: true });
    await expect(action).toHaveAttribute("href", "/teacher/attendance");
    await expect(page.getByText("В саду: 2", { exact: true })).toBeVisible();
    await expect(page.getByText("Без отметки: 3", { exact: true })).toBeVisible();
    await expect(page.getByText("Уточнить приход: 1", { exact: true })).toBeVisible();
    const nav = page.getByRole("navigation", { name: "Разделы воспитателя" });
    await expect(nav.getByRole("link", { name: "Сегодня", exact: true })).toHaveAttribute("aria-current", "page");
    await expect(page.getByRole("link", { name: "Журнал действий" })).toHaveCount(0);
    await expect(page.locator(".app-header")).toHaveCSS("background-color", "rgb(23, 26, 59)");
    await action.focus();
    await expect(action).toBeFocused();
    expect(await action.evaluate((node) => getComputedStyle(node).outlineStyle)).toBe("solid");
    await noOverflow(page);
    await action.click();
    await expect(page.getByLabel("Дата")).toHaveValue(today.date);
    await expect(page.getByText("Без отметки", { exact: true })).toBeVisible();
    await noOverflow(page);
  });

  test(`parent one status card and three usable tabs at ${width}px`, async ({ page }) => {
    await fixtures(page, "PARENT");
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/parent");
    await expect(page.getByRole("article", { name: "Статус ребёнка" })).toHaveCount(1);
    await expect(page.getByRole("article", { name: "Статус ребёнка" })).toContainText("В саду");
    const tabs = page.getByRole("navigation", { name: "Разделы кабинета" });
    await expect(tabs.getByRole("button")).toHaveCount(3);
    for (const button of await tabs.getByRole("button").all()) {
      const box = await button.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
      expect(box?.width).toBeGreaterThanOrEqual(44);
    }
    await page.getByLabel("Ребёнок").selectOption(childB.id);
    await expect(page.getByRole("article", { name: "Статус ребёнка" })).toContainText("Отсутствует");
    await expect(page.getByText("Приход: 08:15")).toHaveCount(0);
    await noOverflow(page);
    await tabs.getByRole("button", { name: "Сообщения", exact: true }).click();
    await expect(page.getByText("Синтетическое сообщение", { exact: true })).toBeVisible();
    await noOverflow(page);
    await page.getByRole("button", { name: "Обновить диалог" }).click();
    await expect(page.getByText("Синтетическое сообщение", { exact: true })).toBeVisible();
    await tabs.getByRole("button", { name: "Объявления", exact: true }).click();
    await expect(page.getByText("Новых объявлений нет.")).toBeVisible();
  });
}

test("parent loaded status is cleared on focus when ChildGuardian is revoked and retry reauthorizes", async ({ page }) => {
  await fixtures(page, "PARENT");
  let revoked = false;
  await page.route(`**/api/v1/parent/children/${child.id}/today`, (route) => route.fulfill(revoked ? { status: 403, json: { error: { code: "FORBIDDEN" } } } : { json: today }));
  await page.goto("/parent");
  await expect(page.getByText("Приход: 08:15")).toBeVisible();
  revoked = true;
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.getByRole("alert").filter({ hasText: "Действие недоступно" })).toBeVisible();
  await expect(page.getByRole("article", { name: "Статус ребёнка" })).toHaveCount(0);
  await expect(page.getByText("Музыка", { exact: true })).toHaveCount(0);
  revoked = false;
  await page.getByRole("button", { name: "Повторить загрузку" }).click();
  await expect(page.getByText("Приход: 08:15")).toBeVisible();
});

test("teacher loaded Today clears privileged cards after assignment revocation", async ({ page }) => {
  await fixtures(page, "TEACHER");
  let revoked = false;
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill(revoked ? { status: 403, json: { error: { code: "FORBIDDEN" } } } : { json: teacherToday }));
  await page.goto("/teacher");
  await expect(page.getByText("В саду: 2", { exact: true })).toBeVisible();
  revoked = true;
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.getByRole("alert").filter({ hasText: "Действие недоступно" })).toBeVisible();
  await expect(page.getByText("В саду: 2", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Отметить посещаемость", exact: true })).toHaveCount(0);
});

test("parent refreshing a revoked dialog clears message content", async ({ page }) => {
  await fixtures(page, "PARENT");
  await page.goto("/parent");
  await page.getByRole("button", { name: "Сообщения", exact: true }).click();
  await expect(page.getByText("Синтетическое сообщение", { exact: true })).toBeVisible();
  await page.route("**/api/v1/parent/communications/v2/threads/*/messages", (route) => route.fulfill({ status: 404, json: { error: { code: "NOT_FOUND" } } }));
  await page.getByRole("button", { name: "Обновить диалог" }).click();
  await expect(page.getByText("Запись не найдена.")).toBeVisible();
  await expect(page.getByText("Синтетическое сообщение", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Отправить", exact: true })).toBeDisabled();
});

test("role cabinets reflow at 200 percent with reduced motion and keyboard navigation", async ({ page }) => {
  for (const role of ["TEACHER", "PARENT"] as const) {
    await fixtures(page, role);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 768, height: 900 });
    await page.goto(role === "TEACHER" ? "/teacher" : "/parent");
    await expect(page.getByRole("heading", { name: role === "TEACHER" ? "Кабинет воспитателя" : "Кабинет родителя" })).toBeVisible();
    // Chromium CSS zoom exercises 200% reflow, including native form controls.
    await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
    await noOverflow(page);
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe("BODY");
    await page.evaluate(() => { document.documentElement.style.zoom = ""; });
  }
});

test("parent distinguishes loading, no linked children and server-confirmed needs-arrival", async ({ page }) => {
  await fixtures(page, "PARENT");
  let release!: () => void;
  await page.route("**/api/v1/parent/children", async (route) => {
    await new Promise<void>((resolve) => { release = resolve; });
    await route.fulfill({ json: [] });
  });
  await page.goto("/parent");
  await expect(page.getByRole("status")).toHaveText("Загружаем карточки детей…");
  await expect.poll(() => Boolean(release)).toBe(true);
  release();
  await expect(page.getByRole("status")).toHaveText("Нет доступных карточек детей.");
  await page.unroute("**/api/v1/parent/children");
  await page.route(`**/api/v1/parent/children/${child.id}/today`, (route) => route.fulfill({ json: { ...today, attendance: { status: "present", arrival_time: null, departure_time: null } } }));
  await page.reload();
  await expect(page.getByRole("article", { name: "Статус ребёнка" })).toContainText("Уточнить приход");
  await expect(page.getByText("В саду", { exact: true })).toHaveCount(0);
});

for (const section of ["groups", "schedule"] as const) {
  test(`teacher ${section} discards late Group A data and clears on revoked access`, async ({ page }) => {
    await fixtures(page, "TEACHER");
    const api = section === "groups" ? `**/api/v1/teacher/groups/${group.id}/children` : `**/api/v1/teacher/schedule?group_id=${group.id}`;
    const apiB = section === "groups" ? `**/api/v1/teacher/groups/${groupB.id}/children` : `**/api/v1/teacher/schedule?group_id=${groupB.id}`;
    let release!: () => void;
    let revoked = false;
    const value = (title: string) => section === "groups" ? [{ ...child, first_name: title }] : [{ id: title, group_id: group.id, weekday: 0, start_time: "09:00:00", end_time: "10:00:00", title }];
    await page.route(api, async (route) => { await new Promise<void>((resolve) => { release = resolve; }); await route.fulfill({ json: value("Старый контекст") }); });
    await page.route(apiB, (route) => route.fulfill(revoked ? { status: 403, json: { error: { code: "FORBIDDEN" } } } : { json: value("Актуальный контекст") }));
    await page.goto(`/teacher/${section}`);
    await expect.poll(() => Boolean(release)).toBe(true);
    await page.getByLabel("Группа").selectOption(groupB.id);
    await expect(page.getByText(/Актуальный контекст/)).toBeVisible();
    const lateResponse = page.waitForResponse((response) => response.url().includes(section === "groups" ? `/groups/${group.id}/children` : `schedule?group_id=${group.id}`));
    release();
    await lateResponse;
    await expect(page.getByText(/Старый контекст/)).toHaveCount(0);
    revoked = true;
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    await expect(page.getByRole("alert").filter({ hasText: "Действие недоступно" })).toBeVisible();
    await expect(page.getByText(/Актуальный контекст/)).toHaveCount(0);
  });
}

test("parent list revalidation removing Child A hides its Group and teachers immediately in Child B context", async ({ page }) => {
  await fixtures(page, "PARENT");
  let removed = false;
  await page.route("**/api/v1/parent/children", (route) => route.fulfill({ json: removed ? [childB] : [child, childB] }));
  const groupThread = { ...thread, thread_type: "group", child_id: null, child_name: null, guardian_id: null, teacher_employee_id: null, teacher_name: null };
  await page.route("**/api/v1/parent/communications/v2/threads", (route) => route.fulfill({ json: [groupThread] }));
  await page.route(`**/api/v1/parent/children/${child.id}/teachers`, (route) => route.fulfill({ json: [{ employee_id: "teacher-a", display_name: "Воспитатель Старой Группы", group_id: group.id, group_name: group.name }] }));
  let releaseToday!: () => void;
  let releaseTeachers!: () => void;
  await page.route(`**/api/v1/parent/children/${childB.id}/today`, async (route) => { await new Promise<void>((resolve) => { releaseToday = resolve; }); await route.fulfill({ json: { ...today, child: childB, group: groupB } }); });
  await page.route(`**/api/v1/parent/children/${childB.id}/teachers`, async (route) => { await new Promise<void>((resolve) => { releaseTeachers = resolve; }); await route.fulfill({ json: [] }); });
  await page.goto("/parent");
  await expect(page.getByRole("article", { name: "Статус ребёнка" })).toBeVisible();
  const initialReload = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/parent/children"));
  await page.getByRole("button", { name: "Сообщения", exact: true }).click();
  await expect(page.getByLabel("Воспитатель")).toContainText("Воспитатель Старой Группы");
  await expect(page.getByText("Синтетическое сообщение", { exact: true })).toBeVisible();
  await initialReload;
  await expect(page.getByLabel("Ребёнок").locator("option")).toHaveCount(2);
  removed = true;
  await page.getByRole("button", { name: "Обновить диалог" }).click();
  await expect(page.getByLabel("Ребёнок")).toHaveValue(childB.id);
  await expect(page.getByLabel("Воспитатель").locator("option")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Личный диалог", exact: true })).toBeDisabled();
  await expect(page.getByText("Синтетическое сообщение", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Группа · Ромашка", exact: true })).toHaveCount(0);
  await expect.poll(() => Boolean(releaseToday && releaseTeachers)).toBe(true);
  releaseToday(); releaseTeachers();
});

test("parent dialog refresh can retry a temporary server error without losing the draft", async ({ page }) => {
  await fixtures(page, "PARENT");
  await page.goto("/parent");
  await page.getByRole("button", { name: "Сообщения", exact: true }).click();
  await expect(page.getByText("Синтетическое сообщение", { exact: true })).toBeVisible();
  await page.getByLabel("Ответ").fill("Синтетический черновик");
  await page.route("**/api/v1/parent/communications/v2/threads/*/messages", (route) => route.fulfill({ status: 503, json: { error: { code: "INTERNAL_ERROR" } } }));
  await page.getByRole("button", { name: "Обновить диалог" }).click();
  await expect(page.getByText("Не удалось выполнить запрос. Попробуйте ещё раз.")).toBeVisible();
  await expect(page.getByLabel("Ответ")).toHaveValue("Синтетический черновик");
  await expect(page.getByRole("button", { name: "Обновить диалог" })).toBeEnabled();
  await page.unroute("**/api/v1/parent/communications/v2/threads/*/messages");
  await page.getByRole("button", { name: "Обновить диалог" }).click();
  await expect(page.getByText("Синтетическое сообщение", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Ответ")).toHaveValue("Синтетический черновик");
});
