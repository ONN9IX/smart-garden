/** PARENT cabinet keeps announcements and communications while deferred modules stay hidden. */
import { expect, test } from "@playwright/test";

const parent = { user: { id: "00000000-0000-4000-8000-000000000621", username: "parent-demo", role: "PARENT", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };
const child = { id: "00000000-0000-4000-8000-000000000612", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null };
const childB = { id: "00000000-0000-4000-8000-000000000632", first_name: "Второй", last_name: "Ребёнок", middle_name: null };
const groupId = "00000000-0000-4000-8000-000000000611";
const groupBId = "00000000-0000-4000-8000-000000000633";
const teacherId = "00000000-0000-4000-8000-000000000630";
const teacherBId = "00000000-0000-4000-8000-000000000634";
const thread = { id: "00000000-0000-4000-8000-000000000625", thread_type: "direct", group_id: groupId, group_name: "Ромашка", audience: "all", child_id: child.id, child_name: "Ребёнок Тестовый", guardian_id: "00000000-0000-4000-8000-000000000626", teacher_employee_id: teacherId, teacher_name: "Воспитатель Тестовый", last_message_id: null, last_message_at: null, preview: null, unread_count: 0 };
let threads: typeof thread[] = [];
const announcement = { id: "00000000-0000-4000-8000-000000000622", target_type: "group", group_id: groupId, group_name: "Ромашка", audience: "parents", title: "Объявление группы", body: "Синтетический текст", status: "active", archived_at: null, published_at: "2026-09-30T10:00:00Z", unread: true, recipient_count: 1, can_manage: false };
let readAnnouncementIds: string[] = [];

test.beforeEach(async ({ page }) => {
  threads = [];
  readAnnouncementIds = [];
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(parent) }));
  await page.route("**/api/v1/parent/children", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child]) }));
  await page.route(`**/api/v1/parent/children/${child.id}/today`, (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      date: "2026-09-30",
      child,
      group: { id: groupId, name: "Ромашка" },
      attendance: { status: "present", arrival_time: "08:15:00", departure_time: null },
      schedule: [{ id: "00000000-0000-4000-8000-000000000629", group_id: groupId, weekday: 2, start_time: "09:00:00", end_time: "09:30:00", title: "Музыка" }],
    }),
  }));
  await page.route("**/api/v1/communications/v2/announcements", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement]) }));
  await page.route(`**/api/v1/communications/v2/announcements/${announcement.id}`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(announcement) }));
  await page.route("**/api/v1/parent/communications/v2/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(threads) }));
  await page.route(`**/api/v1/parent/children/${child.id}/teachers`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ employee_id: teacherId, display_name: "Воспитатель Тестовый", group_id: groupId, group_name: "Ромашка" }]) }));
  await page.route("**/api/v1/parent/communications/v2/groups/*/thread", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...thread, thread_type: "group", teacher_employee_id: null, teacher_name: null, child_id: null, child_name: null, guardian_id: null }) }));
  await page.route("**/api/v1/parent/communications/v2/direct", async (route) => {
    threads = [thread];
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(thread) });
  });
  await page.route("**/api/v1/parent/communications/v2/threads/*/messages", (route) => route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, contentType: "application/json", body: route.request().method() === "POST" ? JSON.stringify({ id: "00000000-0000-4000-8000-000000000627", thread_id: thread.id, sender_user_id: parent.user.id, sender_role: "PARENT", sender_name: "Родитель Тестовый", body: "Ответ родителя", created_at: "2026-09-30T10:05:00Z" }) : JSON.stringify([{ id: "00000000-0000-4000-8000-000000000628", thread_id: thread.id, sender_user_id: "00000000-0000-4000-8000-000000000601", sender_role: "TEACHER", sender_name: "Воспитатель Тестовый", body: "Сообщение воспитателя", created_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/parent/communications/v2/threads/*/read", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ thread_id: thread.id, last_read_message_id: "00000000-0000-4000-8000-000000000628", last_read_at: "2026-09-30T10:00:00Z" }) }));
  await page.route("**/api/v1/communications/v2/announcements/*/read", (route) => {
    const id = route.request().url().split("/").at(-2) || "";
    readAnnouncementIds.push(id);
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ announcement_id: id, read_at: "2026-09-30T10:00:00Z" }) });
  });
});

test("parent sees daily child overview and only enabled modules", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/parent");
  await expect(page.getByRole("heading", { name: "Кабинет родителя" })).toBeVisible();
  await expect(page.locator(".auth-brand")).toContainText("ПРОМАКС");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole("button", { name: "Сегодня" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("heading", { name: "Группа Ромашка" })).toBeVisible();
  await expect(page.getByText("Ежедневная информация")).toBeVisible();
  await expect(page.getByText("В детском саду")).toBeVisible();
  await expect(page.getByText("Приход: 08:15")).toBeVisible();
  await expect(page.getByText("Музыка")).toBeVisible();
  for (const label of ["Дневник", "Опросы", "Фото"]) {
    await expect(page.getByRole("button", { name: label })).toHaveCount(0);
  }
  await page.getByRole("button", { name: "Объявления" }).click();
  await expect(page.getByText("Объявление группы")).toBeVisible();
  expect(readAnnouncementIds).toEqual([]);
  await page.getByRole("button", { name: "Объявление группы" }).click();
  await expect(page.getByText("Синтетический текст")).toBeVisible();
  await expect.poll(() => readAnnouncementIds).toEqual([announcement.id]);
  await expect(page.getByRole("button", { name: "Сообщения" })).toBeVisible();
});

test("parent hides stale announcement list content when detail access is revoked", async ({ page }) => {
  let detailCalls = 0;
  let readCalls = 0;
  await page.route(`**/api/v1/communications/v2/announcements/${announcement.id}`, async (route) => {
    detailCalls += 1;
    await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { code: "NOT_FOUND" } }) });
  });
  await page.route(`**/api/v1/communications/v2/announcements/${announcement.id}/read`, async (route) => {
    readCalls += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ announcement_id: announcement.id, read_at: "2026-09-30T10:00:00Z" }) });
  });
  await page.goto("/parent");
  await page.getByRole("button", { name: "Объявления" }).click();
  await expect(page.getByRole("button", { name: "Объявление группы" })).toBeVisible();
  await expect(page.getByText("Синтетический текст")).toHaveCount(0);
  await page.getByRole("button", { name: "Объявление группы" }).click();
  await expect(page.getByText("Объявление больше недоступно.")).toBeVisible();
  await expect(page.getByText("Синтетический текст")).toHaveCount(0);
  expect(detailCalls).toBe(1);
  expect(readCalls).toBe(0);
});

test("parent ignores a late announcement detail response after opening another item", async ({ page }) => {
  const otherAnnouncement = { ...announcement, id: "00000000-0000-4000-8000-000000000646", title: "Второе объявление", body: "Второй актуальный текст" };
  await page.route("**/api/v1/communications/v2/announcements", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement, otherAnnouncement]) }));
  let releaseFirst!: () => void;
  let firstRequested!: () => void;
  const firstRequestedPromise = new Promise<void>((resolve) => { firstRequested = resolve; });
  await page.route(`**/api/v1/communications/v2/announcements/${announcement.id}`, async (route) => {
    firstRequested();
    await new Promise<void>((resolve) => { releaseFirst = resolve; });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(announcement) });
  });
  await page.route(`**/api/v1/communications/v2/announcements/${otherAnnouncement.id}`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(otherAnnouncement) }));
  await page.goto("/parent");
  await page.getByRole("button", { name: "Объявления" }).click();
  await page.getByRole("button", { name: announcement.title }).click();
  await firstRequestedPromise;
  await page.getByRole("button", { name: otherAnnouncement.title }).click();
  await expect(page.getByText(otherAnnouncement.body)).toBeVisible();
  releaseFirst();
  await expect(page.getByText(announcement.body)).toHaveCount(0);
  await expect(page.getByText(otherAnnouncement.body)).toBeVisible();
});

test("parent removes an opened announcement if its read authorization is revoked", async ({ page }) => {
  let denyRead!: () => void;
  let readRequested!: () => void;
  const readRequestedPromise = new Promise<void>((resolve) => { readRequested = resolve; });
  const denied = new Promise<void>((resolve) => { denyRead = resolve; });
  await page.route(`**/api/v1/communications/v2/announcements/${announcement.id}/read`, async (route) => {
    readRequested();
    await denied;
    await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { code: "NOT_FOUND" } }) });
  });
  await page.goto("/parent");
  await page.getByRole("button", { name: "Объявления" }).click();
  await page.getByRole("button", { name: announcement.title }).click();
  await readRequestedPromise;
  await expect(page.getByText(announcement.body)).toHaveCount(0);
  denyRead();
  await expect(page.getByText("Объявление больше недоступно.")).toBeVisible();
  await expect(page.getByText(announcement.body)).toHaveCount(0);
});

test("parent child switch filters conversations and ignores a late private response", async ({ page }) => {
  const directB = { ...thread, id: "00000000-0000-4000-8000-000000000635", child_id: childB.id, child_name: "Ребёнок Второй", group_id: groupBId, group_name: "Василёк", teacher_employee_id: teacherBId, teacher_name: "Воспитатель Второй" };
  const secondTeacherThread = { ...thread, id: "00000000-0000-4000-8000-000000000640", teacher_employee_id: "00000000-0000-4000-8000-000000000641", teacher_name: "Воспитатель Третий" };
  const groupA = { ...thread, id: "00000000-0000-4000-8000-000000000636", thread_type: "group", child_id: null, child_name: null, guardian_id: null, teacher_employee_id: null, teacher_name: null };
  const groupB = { ...groupA, id: "00000000-0000-4000-8000-000000000637", group_id: groupBId, group_name: "Василёк" };
  await page.route("**/api/v1/parent/children", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child, childB]) }));
  await page.route(`**/api/v1/parent/children/${childB.id}/today`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", child: childB, group: { id: groupBId, name: "Василёк" }, attendance: { status: "unknown", arrival_time: null, departure_time: null }, schedule: [] }) }));
  await page.route(`**/api/v1/parent/children/${childB.id}/teachers`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ employee_id: teacherBId, display_name: "Воспитатель Второй", group_id: groupBId, group_name: "Василёк" }]) }));
  await page.route("**/api/v1/parent/communications/v2/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([thread, secondTeacherThread, groupA, directB, groupB]) }));
  let releaseA!: () => void;
  let markARequested!: () => void;
  const aRequested = new Promise<void>((resolve) => { markARequested = resolve; });
  await page.route(`**/api/v1/parent/communications/v2/threads/${thread.id}/messages`, async (route) => {
    markARequested();
    await new Promise<void>((resolve) => { releaseA = resolve; });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000638", thread_id: thread.id, sender_user_id: "other", sender_role: "TEACHER", sender_name: "Воспитатель", body: "Старый приватный текст", created_at: "2026-09-30T10:00:00Z" }]) });
  });
  await page.route(`**/api/v1/parent/communications/v2/threads/${directB.id}/messages`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000639", thread_id: directB.id, sender_user_id: "other", sender_role: "TEACHER", sender_name: "Воспитатель Второй", body: "Сообщение второго ребёнка", created_at: "2026-09-30T10:01:00Z" }]) }));
  await page.goto("/parent");
  await page.setViewportSize({ width: 320, height: 780 });
  await page.getByRole("button", { name: "Сообщения" }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole("button", { name: /Воспитатель Тестовый/ })).toBeVisible();
  await aRequested;
  await expect(page.getByRole("button", { name: /Воспитатель Третий/ })).toBeVisible();
  await page.getByLabel("Ребёнок").selectOption(childB.id);
  await expect(page.getByRole("button", { name: /Воспитатель Второй/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Воспитатель Тестовый/ })).toHaveCount(0);
  await expect(page.getByText("Старый приватный текст")).toHaveCount(0);
  await expect(page.getByText("Сообщение второго ребёнка")).toBeVisible();
  releaseA();
  await expect(page.getByText("Старый приватный текст")).toHaveCount(0);
});

test("parent bootstraps direct chat from linked child", async ({ page }) => {
  await page.goto("/parent");
  await page.getByRole("button", { name: "Сообщения" }).click();
  await expect(page.getByLabel("Ребёнок")).toHaveValue(child.id);
  await expect(page.getByRole("button", { name: "Отправить" })).toBeDisabled();
  await page.getByRole("button", { name: "Личный диалог" }).click();
  await expect(page.getByRole("button", { name: /Воспитатель Тестовый · Ребёнок Тестовый/ })).toBeVisible();
  await expect(page.getByText("Сообщение воспитателя")).toBeVisible();
  await expect(page.locator("li strong", { hasText: "Воспитатель Тестовый" })).toBeVisible();
  await page.getByLabel("Ответ").fill("Ответ родителя");
  await page.getByRole("button", { name: "Отправить" }).click();
});

test("parent keeps an uncertain message draft and reuses its id on retry", async ({ page }) => {
  const clientIds: string[] = [];
  await page.route(`**/api/v1/parent/communications/v2/threads/${thread.id}/messages`, async (route) => {
    if (route.request().method() !== "POST") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000628", thread_id: thread.id, sender_user_id: "other", sender_role: "TEACHER", sender_name: "Воспитатель Тестовый", body: "Синтетическое сообщение", created_at: "2026-09-30T10:00:00Z" }]) });
    }
    clientIds.push(route.request().postDataJSON().client_message_id);
    if (clientIds.length === 1) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { code: "INTERNAL_ERROR" } }) });
    return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: "00000000-0000-4000-8000-000000000627", thread_id: thread.id, sender_user_id: parent.user.id, sender_role: "PARENT", sender_name: "Родитель Тестовый", body: "Повторная отправка", created_at: "2026-09-30T10:05:00Z" }) });
  });
  await page.goto("/parent");
  await page.getByRole("button", { name: "Сообщения" }).click();
  await page.getByRole("button", { name: "Личный диалог" }).click();
  await page.getByLabel("Ответ").fill("Повторная отправка");
  await page.getByRole("button", { name: "Отправить" }).click();
  await expect(page.getByText("Не удалось выполнить запрос. Попробуйте ещё раз.")).toBeVisible();
  await expect(page.getByLabel("Ответ")).toHaveValue("Повторная отправка");
  await page.getByRole("button", { name: "Отправить" }).click();
  await expect.poll(() => clientIds).toHaveLength(2);
  expect(clientIds[1]).toBe(clientIds[0]);
  await expect(page.getByLabel("Ответ")).toHaveValue("");
});

test("parent hides an open conversation after the server revokes access", async ({ page }) => {
  await page.route(`**/api/v1/parent/communications/v2/threads/${thread.id}/messages`, (route) => {
    if (route.request().method() === "POST") return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { code: "NOT_FOUND" } }) });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000645", thread_id: thread.id, sender_user_id: "other", sender_role: "TEACHER", sender_name: "Воспитатель Тестовый", body: "Приватное до отзыва", created_at: "2026-09-30T10:00:00Z" }]) });
  });
  await page.goto("/parent");
  await page.getByRole("button", { name: "Сообщения" }).click();
  await page.getByRole("button", { name: "Личный диалог" }).click();
  await expect(page.getByText("Приватное до отзыва")).toBeVisible();
  await page.getByLabel("Ответ").fill("Синтетический черновик");
  await page.getByRole("button", { name: "Отправить" }).click();
  await expect(page.getByText("Приватное до отзыва")).toHaveCount(0);
  await expect(page.getByLabel("Ответ")).toHaveValue("Синтетический черновик");
});
