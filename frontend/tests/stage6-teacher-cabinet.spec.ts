/** Enabled TEACHER cabinet flow plus deferred-module visibility gates. */
import { expect, test } from "@playwright/test";

const group = { id: "00000000-0000-4000-8000-000000000611", name: "Ромашка" };
const otherGroup = { id: "00000000-0000-4000-8000-000000000651", name: "Солнышко" };
const child = { id: "00000000-0000-4000-8000-000000000612", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null, status: "active" };
const childB = { id: "00000000-0000-4000-8000-000000000652", first_name: "Второй", last_name: "Синтетический", middle_name: null, status: "active" };
const guardian = { id: "00000000-0000-4000-8000-000000000613", child_id: child.id, first_name: "Тестовый", last_name: "Родитель", middle_name: null, relation_type: "mother", phone: "+70000000000", email: null, can_message: true };
const thread = { id: "00000000-0000-4000-8000-000000000615", thread_type: "direct", group_id: group.id, audience: "all", child_id: child.id, guardian_id: guardian.id, created_at: "2026-09-30T09:00:00Z" };
const teacher = { user: { id: "00000000-0000-4000-8000-000000000601", username: "teacher-demo", role: "TEACHER", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(teacher) }));
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [group], schedule: [], attendance: [{ group_id: group.id, active_children: 1, present: 1, on_site: 0, departed: 1, absent: 0, unknown: 0, needs_arrival: 0 }], tasks: [], notifications: [], unread_communication_count: 1 }) }));
  await page.route("**/api/v1/teacher/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/children`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/guardians`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([guardian]) }));
  await page.route("**/api/v1/teacher/attendance?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: null, date: "2026-09-30", child, group, status: "unknown", arrival_time: null, departure_time: null }]) }));
  await page.route("**/api/v1/teacher/attendance", (route) => route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: null, departure_time: null }) }));
  await page.route("**/api/v1/teacher/attendance/arrival", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: "08:15:00", departure_time: null }) }));
  await page.route("**/api/v1/teacher/attendance/departure", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: "08:15:00", departure_time: "17:05:00" }) }));
  await page.route("**/api/v1/teacher/tasks", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.route("**/api/v1/teacher/notifications", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
});

test("teacher completes daily flow and sees only enabled modules", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/teacher");
  await expect(page.getByRole("heading", { name: "Кабинет воспитателя" })).toBeVisible();
  await expect(page.getByLabel("ПРОМАКС — главная")).toBeVisible();
  await expect(page.getByText(/Ушли: 1/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("link", { name: "Мои группы", exact: true }).click();
  await expect(page.getByText("Тестовый Ребёнок")).toBeVisible();
  await expect(page.getByText("Мама · можно написать")).toBeVisible();
  await page.getByRole("link", { name: "Посещаемость" }).click();
  await expect(page.getByLabel("Дата")).toHaveValue("2026-09-30");
  await expect(page.getByText("Без отметки")).toBeVisible();
  const arrival = page.waitForRequest("**/api/v1/teacher/attendance/arrival");
  await page.getByRole("button", { name: "Пришёл" }).click();
  expect((await arrival).postDataJSON()).toEqual({ child_id: child.id });
  await page.getByRole("link", { name: "Задачи и уведомления" }).click();
  await expect(page.getByRole("heading", { name: "Задачи и уведомления" })).toBeVisible();
  for (const label of ["Дневник", "Опросы", "События", "Фото"]) {
    await expect(page.getByRole("link", { name: label })).toHaveCount(0);
  }
  await expect(page.getByText("Документы к ознакомлению")).toHaveCount(0);
});

test("teacher records arrival and departure inline and renders only confirmed server state", async ({ page }) => {
  let row = { record_id: null as string | null, date: "2026-09-30", child, group, status: "unknown", arrival_time: null as string | null, departure_time: null as string | null };
  await page.route("**/api/v1/teacher/attendance?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([row]) }));
  await page.route("**/api/v1/teacher/attendance/arrival", async (route) => {
    row = { ...row, record_id: "00000000-0000-4000-8000-000000000614", status: "present", arrival_time: "08:15:00" };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(row) });
  });
  await page.route("**/api/v1/teacher/attendance/departure", async (route) => {
    row = { ...row, departure_time: "17:05:00" };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(row) });
  });
  await page.goto("/teacher/attendance");
  await expect(page.getByText("Без отметки")).toBeVisible();
  await page.getByRole("button", { name: "Пришёл" }).click();
  await expect(page.getByText("В саду")).toBeVisible();
  await expect(page.getByText("Пришёл: 08:15")).toBeVisible();
  await page.getByRole("button", { name: "Ушёл" }).click();
  await expect(page.getByText("Ушёл", { exact: true })).toBeVisible();
  await expect(page.getByText("Пришёл: 08:15 · Ушёл: 17:05")).toBeVisible();
  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 820 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

test("teacher does not show arrival after a rejected write", async ({ page }) => {
  await page.route("**/api/v1/teacher/attendance/arrival", (route) => route.fulfill({
    status: 403, contentType: "application/json", body: JSON.stringify({ error: { code: "FORBIDDEN", message: "Доступ запрещён." } }),
  }));
  await page.goto("/teacher/attendance");
  await page.getByRole("button", { name: "Пришёл" }).click();
  await expect(page.getByText("Без отметки")).toBeVisible();
  await expect(page.getByText("Действие недоступно для вашей учётной записи.")).toBeVisible();
  await expect(page.getByText("В саду", { exact: true })).toHaveCount(0);
});

test("teacher attendance clears and ignores stale rows across group A to B to A", async ({ page }) => {
  await page.route("**/api/v1/teacher/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group, otherGroup]) }));
  let groupACalls = 0;
  let releaseFirstA!: () => void;
  let markFirstA!: () => void;
  const firstARequested = new Promise<void>((resolve) => { markFirstA = resolve; });
  await page.route("**/api/v1/teacher/attendance?**", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("group_id") === group.id) {
      groupACalls += 1;
      if (groupACalls === 1) {
        markFirstA();
        await new Promise<void>((resolve) => { releaseFirstA = resolve; });
        return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: null, date: "2026-09-30", child, group, status: "absent", arrival_time: null, departure_time: null }]) });
      }
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: null, date: "2026-09-30", child: childB, group, status: "unknown", arrival_time: null, departure_time: null }]) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: null, date: "2026-09-30", child: childB, group: otherGroup, status: "present", arrival_time: "08:30:00", departure_time: null }]) });
  });
  await page.setViewportSize({ width: 360, height: 820 });
  await page.goto("/teacher/attendance");
  await firstARequested;
  await page.getByLabel("Группа").selectOption(otherGroup.id);
  await expect(page.getByText("Второй Синтетический")).toBeVisible();
  await expect(page.getByText("Тестовый Ребёнок")).toHaveCount(0);
  await page.getByLabel("Группа").selectOption(group.id);
  await expect(page.getByText("Без отметки")).toBeVisible();
  releaseFirstA();
  await expect(page.getByText("Тестовый Ребёнок", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Второй Синтетический")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("teacher keeps schedule, communications, announcements, tasks and notifications", async ({ page }) => {
  await page.route("**/api/v1/teacher/schedule?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000616", group_id: group.id, weekday: 2, start_time: "09:00:00", end_time: "09:30:00", title: "Музыка" }]) }));
  await page.goto("/teacher/schedule");
  await expect(page.getByText("Музыка")).toBeVisible();

  const v2Thread = { ...thread, group_name: group.name, child_name: "Ребёнок Тестовый", teacher_employee_id: "00000000-0000-4000-8000-000000000631", teacher_name: "Воспитатель Тестовый", last_message_id: "00000000-0000-4000-8000-000000000618", last_message_at: "2026-09-30T10:00:00Z", preview: "Сообщение родителя", unread_count: 1 };
  await page.route("**/api/v1/teacher/communications/v2/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([v2Thread]) }));
  await page.route("**/api/v1/teacher/communications/v2/threads/*/messages", (route) => route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, contentType: "application/json", body: route.request().method() === "POST" ? JSON.stringify({ id: "00000000-0000-4000-8000-000000000617", thread_id: thread.id, sender_user_id: teacher.user.id, sender_role: "TEACHER", sender_name: "Воспитатель Тестовый", body: "Ответ воспитателя", created_at: "2026-09-30T10:10:00Z" }) : JSON.stringify([{ id: "00000000-0000-4000-8000-000000000618", thread_id: thread.id, sender_user_id: "00000000-0000-4000-8000-000000000621", sender_role: "PARENT", sender_name: "Родитель Тестовый", body: "Сообщение родителя", created_at: "2026-09-30T10:00:00Z" }]) }));
  await page.route("**/api/v1/teacher/communications/v2/threads/*/read", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ thread_id: thread.id, last_read_message_id: "00000000-0000-4000-8000-000000000618", last_read_at: "2026-09-30T10:00:00Z" }) }));
  await page.setViewportSize({ width: 320, height: 780 });
  await page.goto("/teacher/communications");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole("heading", { name: "Сообщения", level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: /Родитель Тестовый · Мама · Ребёнок Тестовый/ })).toBeVisible();
  await expect(page.locator("li > span > span", { hasText: "Сообщение родителя" })).toBeVisible();
  await expect(page.getByText("Родитель Тестовый", { exact: true })).toBeVisible();

  const announcement = { id: "00000000-0000-4000-8000-000000000625", target_type: "group", group_id: group.id, group_name: group.name, audience: "parents", title: "Напоминание", body: "Синтетический текст", status: "active", archived_at: null, published_at: "2026-09-30T10:00:00Z", unread: false, recipient_count: 1, can_manage: true };
  await page.route("**/api/v1/communications/v2/announcements?status=all", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement]) }));
  let previewCalls = 0;
  let publishCalls = 0;
  await page.route("**/api/v1/communications/v2/announcements/preview", async (route) => {
    previewCalls += 1;
    expect(route.request().postDataJSON()).toEqual({ target_type: "group", group_id: group.id, audience: "parents" });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ recipient_count: 2, parents_count: 2, staff_count: 0 }) });
  });
  await page.route("**/api/v1/communications/v2/announcements", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    publishCalls += 1;
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ ...announcement, id: "00000000-0000-4000-8000-000000000626" }) });
  });
  await page.goto("/teacher/announcements");
  await expect(page.getByText("Напоминание")).toBeVisible();
  await expect(page.getByText("Активно")).toBeVisible();
  await page.getByRole("button", { name: "Опубликовать для группы" }).click();
  await expect(page.getByText("Введите заголовок")).toBeVisible();
  await expect(page.getByText("Введите текст объявления")).toBeVisible();
  await page.getByLabel("Заголовок").fill("Тестовое объявление");
  await page.getByLabel("Текст").fill("Синтетическое содержание");
  await page.getByRole("button", { name: "Проверить аудиторию" }).click();
  await expect(page.getByText(/Получателей: 2 \(родители: 2, сотрудники: 0\)/)).toBeVisible();
  expect(publishCalls).toBe(0);
  await page.getByRole("checkbox", { name: "Подтверждаю выбранную аудиторию и число получателей" }).check();
  await page.getByRole("button", { name: "Опубликовать для группы" }).click();
  await expect.poll(() => publishCalls).toBe(1);
  expect(previewCalls).toBe(1);
});

test("teacher hides the previous chat while a switched conversation is loading", async ({ page }) => {
  const direct = { ...thread, group_name: group.name, child_name: "Ребёнок Тестовый", teacher_employee_id: "00000000-0000-4000-8000-000000000631", teacher_name: "Воспитатель Тестовый", last_message_id: null, last_message_at: null, preview: null, unread_count: 0 };
  const groupThread = { ...direct, id: "00000000-0000-4000-8000-000000000642", thread_type: "group", audience: "all", child_id: null, child_name: null, guardian_id: null, teacher_employee_id: null, teacher_name: null };
  await page.route("**/api/v1/teacher/communications/v2/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([direct, groupThread]) }));
  await page.route("**/api/v1/teacher/communications/v2/threads/*/read", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ thread_id: groupThread.id, last_read_message_id: "00000000-0000-4000-8000-000000000644", last_read_at: "2026-09-30T10:01:00Z" }) }));
  let releaseA!: () => void;
  let markARequested!: () => void;
  const aRequested = new Promise<void>((resolve) => { markARequested = resolve; });
  await page.route("**/api/v1/teacher/communications/v2/threads/*/messages", async (route) => {
    const url = route.request().url();
    if (url.includes(direct.id)) {
      markARequested();
      await new Promise<void>((resolve) => { releaseA = resolve; });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000643", thread_id: direct.id, sender_user_id: "parent", sender_role: "PARENT", sender_name: "Родитель Тестовый", body: "Старый чат воспитателя", created_at: "2026-09-30T10:00:00Z" }]) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000644", thread_id: groupThread.id, sender_user_id: "parent", sender_role: "PARENT", sender_name: "Родитель Тестовый", body: "Сообщение группы", created_at: "2026-09-30T10:01:00Z" }]) });
  });
  await page.goto("/teacher/communications");
  await expect(page.getByRole("button", { name: /Родитель Тестовый · Мама · Ребёнок Тестовый/ })).toBeVisible();
  await aRequested;
  await page.getByRole("button", { name: /Ромашка/ }).click();
  await expect(page.getByText("Старый чат воспитателя")).toHaveCount(0);
  await expect(page.getByText("Сообщение группы")).toBeVisible();
  releaseA();
  await expect(page.getByText("Старый чат воспитателя")).toHaveCount(0);
});

test("teacher announcements discard late responses across A to B and A to B to A switches", async ({ page }) => {
  await page.route("**/api/v1/teacher/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group, otherGroup]) }));
  const announcement = (id: string, targetGroup: typeof group, title: string) => ({
    id, target_type: "group", group_id: targetGroup.id, group_name: targetGroup.name, audience: "parents",
    title, body: `Синтетический текст ${title}`, status: "active", archived_at: null,
    published_at: "2026-09-30T10:00:00Z", unread: false, recipient_count: 1, can_manage: true,
  });
  let releaseInitialA!: () => void;
  let markInitialA!: () => void;
  const initialARequested = new Promise<void>((resolve) => { markInitialA = resolve; });
  let releaseLateB!: () => void;
  let markLateB!: () => void;
  const lateBRequested = new Promise<void>((resolve) => { markLateB = resolve; });
  let calls = 0;
  await page.route("**/api/v1/communications/v2/announcements?status=all", async (route) => {
    calls += 1;
    if (calls === 1) {
      markInitialA();
      await new Promise<void>((resolve) => { releaseInitialA = resolve; });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement("a-old", group, "Старое объявление группы А")]) });
    }
    if (calls === 2) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement("b-first", otherGroup, "Объявление группы Б")]) });
    if (calls === 4) {
      markLateB();
      await new Promise<void>((resolve) => { releaseLateB = resolve; });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement("b-late", otherGroup, "Устаревшее объявление группы Б")]) });
    }
    const title = calls === 3 ? "Новое объявление группы А" : "Обновлённое объявление группы А";
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([announcement(`a-${calls}`, group, title)]) });
  });

  await page.goto("/teacher/announcements");
  await initialARequested;
  const groupPicker = page.getByLabel("Группа");
  await groupPicker.selectOption(otherGroup.id);
  await expect(page.getByText("Объявление группы Б")).toBeVisible();
  releaseInitialA();
  await expect(page.getByText("Старое объявление группы А")).toHaveCount(0);
  await expect(page.getByText("Объявление группы Б")).toBeVisible();

  await groupPicker.selectOption(group.id);
  await expect(page.getByText("Новое объявление группы А")).toBeVisible();
  await groupPicker.selectOption(otherGroup.id);
  await lateBRequested;
  await expect(page.getByText("Устаревшее объявление группы Б")).toHaveCount(0);
  await groupPicker.selectOption(group.id);
  await expect(page.getByText("Обновлённое объявление группы А")).toBeVisible();
  releaseLateB();
  await expect(page.getByText("Устаревшее объявление группы Б")).toHaveCount(0);
  await expect(page.getByText("Обновлённое объявление группы А")).toBeVisible();
  await expect(page.getByRole("button", { name: "Изменить" })).toHaveCount(1);
});

test("teacher announcement audience preview cannot authorize a different Group after switching", async ({ page }) => {
  await page.route("**/api/v1/teacher/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group, otherGroup]) }));
  await page.route("**/api/v1/communications/v2/announcements?status=all", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  let releaseA!: () => void;
  let markPreviewA!: () => void;
  const previewARequested = new Promise<void>((resolve) => { markPreviewA = resolve; });
  let previewCalls = 0;
  await page.route("**/api/v1/communications/v2/announcements/preview", async (route) => {
    previewCalls += 1;
    if (previewCalls === 1) {
      markPreviewA();
      await new Promise<void>((resolve) => { releaseA = resolve; });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ recipient_count: 91, parents_count: 91, staff_count: 0 }) });
    }
    expect(route.request().postDataJSON()).toEqual({ target_type: "group", group_id: otherGroup.id, audience: "parents" });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ recipient_count: 2, parents_count: 2, staff_count: 0 }) });
  });
  let publishedGroupId = "";
  await page.route("**/api/v1/communications/v2/announcements", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    publishedGroupId = route.request().postDataJSON().group_id;
    return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({
      id: "00000000-0000-4000-8000-000000000652", target_type: "group", group_id: otherGroup.id,
      group_name: otherGroup.name, audience: "parents", title: "Второе объявление", body: "Синтетический текст",
      status: "active", archived_at: null, published_at: "2026-09-30T10:00:00Z", unread: false,
      recipient_count: 2, can_manage: true,
    }) });
  });

  await page.goto("/teacher/announcements");
  await page.getByLabel("Заголовок").fill("Первое объявление");
  await page.getByLabel("Текст").fill("Текст первой группы");
  await page.getByRole("button", { name: "Проверить аудиторию" }).click();
  await previewARequested;
  await page.getByLabel("Группа").selectOption(otherGroup.id);
  await page.getByLabel("Заголовок").fill("Второе объявление");
  await page.getByLabel("Текст").fill("Текст второй группы");
  await page.getByRole("button", { name: "Проверить аудиторию" }).click();
  await expect(page.getByText(/Получателей: 2 \(родители: 2, сотрудники: 0\)/)).toBeVisible();
  releaseA();
  await expect(page.getByText(/Получателей: 91/)).toHaveCount(0);
  await page.getByRole("checkbox", { name: "Подтверждаю выбранную аудиторию и число получателей" }).check();
  await page.getByRole("button", { name: "Опубликовать для группы" }).click();
  await expect.poll(() => publishedGroupId).toBe(otherGroup.id);
  expect(previewCalls).toBe(2);
});

test("direct URLs for deferred teacher modules return to teacher home", async ({ page }) => {
  for (const path of ["/teacher/diary", "/teacher/polls", "/teacher/incidents", "/teacher/photos"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/teacher$/);
  }
});

test("teacher empty assignment state remains usable", async ({ page }) => {
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [], schedule: [], attendance: [], tasks: [], notifications: [], unread_communication_count: 0 }) }));
  await page.goto("/teacher");
  await expect(page.getByText("0", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Мои группы", exact: true })).toBeVisible();
});
