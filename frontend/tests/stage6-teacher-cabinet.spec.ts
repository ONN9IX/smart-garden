/** Complete TEACHER cabinet daily flow and isolated navigation. */
import { expect, test } from "@playwright/test";

const group = { id: "00000000-0000-4000-8000-000000000611", name: "Ромашка" };
const child = { id: "00000000-0000-4000-8000-000000000612", first_name: "Тестовый", last_name: "Ребёнок", middle_name: null, status: "active" };
const guardian = { id: "00000000-0000-4000-8000-000000000613", child_id: child.id, first_name: "Тестовый", last_name: "Родитель", middle_name: null, relation_type: "mother", phone: "+70000000000", email: null };
const thread = { id: "00000000-0000-4000-8000-000000000615", thread_type: "direct", group_id: group.id, child_id: child.id, guardian_id: guardian.id, created_at: "2026-09-30T09:00:00Z" };
const teacher = { user: { id: "00000000-0000-4000-8000-000000000601", username: "teacher-demo", role: "TEACHER", status: "active", must_change_password: false }, organization: { id: "00000000-0000-4000-8000-000000000600", name: "Синтетический сад" } };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(teacher) }));
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [group], schedule: [], attendance: [{ group_id: group.id, present: 1, absent: 0, unknown: 0 }], tasks: [], notifications: [], unread_communication_count: 1 }) }));
  await page.route("**/api/v1/teacher/groups", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([group]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/children`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([child]) }));
  await page.route(`**/api/v1/teacher/groups/${group.id}/guardians`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([guardian]) }));
  await page.route("**/api/v1/teacher/attendance?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ record_id: null, date: "2026-09-30", child, group, status: "unknown", arrival_time: null, departure_time: null }]) }));
  await page.route("**/api/v1/teacher/attendance", (route) => route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ record_id: "00000000-0000-4000-8000-000000000614", date: "2026-09-30", child, group, status: "present", arrival_time: null, departure_time: null }) }));
  for (const path of ["tasks", "notifications", "document-notices"]) await page.route(`**/api/v1/teacher/${path}`, (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
});

test("teacher completes the mobile daily flow without management navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/teacher");
  await expect(page.getByRole("heading", { name: "Кабинет воспитателя" })).toBeVisible();
  await expect(page.getByText("Новые сообщения")).toBeVisible();
  await expect(page.getByRole("link", { name: "Сотрудники" })).toHaveCount(0);
  await page.getByRole("link", { name: "Назначенные" }).click();
  await expect(page.getByText("Тестовый Ребёнок")).toBeVisible();
  await expect(page.getByText("+70000000000")).toBeVisible();
  await page.getByRole("link", { name: "Посещаемость" }).click();
  await expect(page.getByText("Тестовый Ребёнок")).toBeVisible();
  await page.getByRole("button", { name: "Пришёл" }).click();
  await page.getByRole("link", { name: "Ещё" }).click();
  await expect(page.getByRole("link", { name: "Дневник" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Фото" })).toBeVisible();
});

test("teacher operational modules expose the frozen daily actions", async ({ page }) => {
  await page.route("**/api/v1/teacher/schedule?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "00000000-0000-4000-8000-000000000616", group_id: group.id, weekday: 2, start_time: "09:00:00", end_time: "09:30:00", title: "Музыка" }]) }));
  await page.goto("/teacher/schedule");
  await expect(page.getByText("Музыка")).toBeVisible();

  await page.route("**/api/v1/teacher/communications/threads", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([thread]) }));
  await page.route("**/api/v1/teacher/communications/threads/*/messages", (route) => route.fulfill({ status: route.request().method() === "POST" ? 201 : 200, contentType: "application/json", body: route.request().method() === "POST" ? JSON.stringify({ id: "00000000-0000-4000-8000-000000000617", thread_id: thread.id, sender_user_id: teacher.user.id, body: "Ответ воспитателя", created_at: "2026-09-30T10:10:00Z" }) : JSON.stringify([{ id: "00000000-0000-4000-8000-000000000618", thread_id: thread.id, sender_user_id: "00000000-0000-4000-8000-000000000621", body: "Сообщение родителя", created_at: "2026-09-30T10:00:00Z" }]) }));
  await page.goto("/teacher/communications");
  await expect(page.getByText("Сообщение родителя")).toBeVisible();
  await page.getByLabel("Новое сообщение").fill("Ответ воспитателя");
  await page.getByRole("button", { name: "Отправить" }).click();

  let diaryEntries = [{ id: "00000000-0000-4000-8000-000000000619", child_id: child.id, group_id: group.id, date: "2026-09-30", author_user_id: teacher.user.id, note: "Хороший день", created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" }];
  await page.route("**/api/v1/teacher/diary?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(diaryEntries) }));
  await page.route("**/api/v1/teacher/diary", async (route) => {
    diaryEntries = [...diaryEntries, { ...diaryEntries[0], id: "00000000-0000-4000-8000-000000000620", note: "Новая запись" }];
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(diaryEntries.at(-1)) });
  });
  await page.route("**/api/v1/teacher/diary/*", async (route) => {
    const id = route.request().url().split("/").at(-1);
    const payload = route.request().postDataJSON() as { note: string };
    diaryEntries = diaryEntries.map((entry) => entry.id === id ? { ...entry, note: payload.note } : entry);
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(diaryEntries.find((entry) => entry.id === id)) });
  });
  await page.goto("/teacher/diary");
  await expect(page.getByText("Хороший день")).toBeVisible();
  await page.getByLabel("Запись").fill("Новая запись");
  await page.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.getByText("Новая запись")).toBeVisible();
  await page.getByRole("button", { name: "Изменить" }).last().click();
  await page.getByLabel("Запись").fill("Исправленная запись");
  await page.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(page.getByText("Исправленная запись")).toBeVisible();

  let announcements = [{ id: "00000000-0000-4000-8000-000000000625", target_type: "group", group_id: group.id, title: "Напоминание", body: "Синтетический текст", status: "active", created_by: teacher.user.id, created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" }];
  await page.route("**/api/v1/teacher/announcements?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(announcements) }));
  await page.route("**/api/v1/teacher/announcements", async (route) => {
    announcements = [...announcements, { ...announcements[0], id: "00000000-0000-4000-8000-000000000626", title: "Новое объявление" }];
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(announcements.at(-1)) });
  });
  await page.route("**/api/v1/teacher/announcements/*", async (route) => {
    const id = route.request().url().split("/").at(-1);
    const payload = route.request().postDataJSON() as { title: string; body: string };
    announcements = announcements.map((item) => item.id === id ? { ...item, ...payload } : item);
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(announcements.find((item) => item.id === id)) });
  });
  await page.route("**/api/v1/teacher/announcements/*/archive", async (route) => {
    const parts = route.request().url().split("/");
    const id = parts.at(-2);
    announcements = announcements.map((item) => item.id === id ? { ...item, status: "archived" } : item);
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(announcements.find((item) => item.id === id)) });
  });
  await page.goto("/teacher/announcements");
  await page.getByLabel("Заголовок").fill("Новое объявление");
  await page.getByLabel("Текст").fill("Только для назначенной группы");
  await page.getByRole("button", { name: "Опубликовать для группы" }).click();
  await expect(page.getByText("Новое объявление")).toBeVisible();
  let createdAnnouncement = page.getByRole("listitem").filter({ hasText: "Новое объявление" });
  await createdAnnouncement.getByRole("button", { name: "Изменить" }).click();
  await page.getByLabel("Заголовок").fill("Исправленное объявление");
  await page.getByLabel("Текст").fill("Исправленный текст");
  await page.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(page.getByText("Исправленное объявление")).toBeVisible();
  createdAnnouncement = page.getByRole("listitem").filter({ hasText: "Исправленное объявление" });
  await createdAnnouncement.getByRole("button", { name: "Архивировать" }).click();
  await expect(createdAnnouncement.getByText("archived")).toBeVisible();

  const poll = { id: "00000000-0000-4000-8000-000000000627", group_id: group.id, question: "Придёте?", status: "active", closes_at: null, created_by: teacher.user.id, created_at: "2026-09-30T10:00:00Z", selected_option_id: null, options: [{ id: "00000000-0000-4000-8000-000000000628", label: "Да", sort_order: 0 }, { id: "00000000-0000-4000-8000-000000000629", label: "Нет", sort_order: 1 }] };
  await page.route("**/api/v1/teacher/polls?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([poll]) }));
  await page.route("**/api/v1/teacher/polls/*/close", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...poll, status: "closed" }) }));
  await page.goto("/teacher/polls");
  await expect(page.getByText("Придёте?")).toBeVisible();
  await page.getByRole("button", { name: "Закрыть" }).click();

  const incident = { id: "00000000-0000-4000-8000-000000000630", group_id: group.id, child_id: null, occurred_at: "2026-09-30T10:00:00Z", category: "operational", description: "Организационное событие", status: "open", reported_by: teacher.user.id, resolved_by: null, created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" };
  await page.route("**/api/v1/teacher/incidents?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([incident]) }));
  await page.route("**/api/v1/teacher/incidents/*", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...incident, status: "resolved", resolved_by: teacher.user.id }) }));
  await page.goto("/teacher/incidents");
  await expect(page.getByText("Организационное событие")).toBeVisible();
  await page.getByRole("button", { name: "Решено" }).click();
});

test("teacher handles tasks, notices, notifications and consent-gated photo upload", async ({ page }) => {
  const task = { id: "00000000-0000-4000-8000-000000000631", group_id: group.id, title: "Проверить материалы", description: null, due_at: null, status: "open", created_at: "2026-09-30T10:00:00Z", updated_at: "2026-09-30T10:00:00Z" };
  const notification = { id: "00000000-0000-4000-8000-000000000632", kind: "task.assigned", entity_type: "teacher_task", entity_id: task.id, read_at: null, created_at: "2026-09-30T10:00:00Z" };
  const notice = { id: "00000000-0000-4000-8000-000000000633", title: "Правила группы", kind: "policy", requires_ack: true, acknowledged_at: null, created_at: "2026-09-30T10:00:00Z" };
  await page.route("**/api/v1/teacher/tasks", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([task]) }));
  await page.route("**/api/v1/teacher/tasks/*", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...task, status: "done" }) }));
  await page.route("**/api/v1/teacher/notifications", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([notification]) }));
  await page.route("**/api/v1/teacher/notifications/*/read", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...notification, read_at: "2026-09-30T10:05:00Z" }) }));
  await page.route("**/api/v1/teacher/document-notices", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([notice]) }));
  await page.route("**/api/v1/teacher/document-notices/*/ack", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...notice, acknowledged_at: "2026-09-30T10:05:00Z" }) }));
  await page.goto("/teacher/more");
  await expect(page.getByText("Проверить материалы")).toBeVisible();
  await page.getByRole("combobox").selectOption("done");
  await page.getByRole("button", { name: "Прочитано" }).click();
  await page.getByRole("button", { name: "Ознакомлен(а)" }).click();

  const consent = { id: "00000000-0000-4000-8000-000000000634", child_id: child.id, status: "granted", scope: "group_photo_report", effective_from: "2026-09-29T10:00:00Z", effective_to: null };
  await page.route("**/api/v1/teacher/photo-consents?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([consent]) }));
  await page.route("**/api/v1/teacher/photos?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await page.route("**/api/v1/teacher/photos", (route) => route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: "00000000-0000-4000-8000-000000000635", group_id: group.id, child_ids: [child.id], mime_type: "image/png", size_bytes: 16, captured_at: null, status: "active", created_at: "2026-09-30T10:00:00Z" }) }));
  await page.goto("/teacher/photos");
  await page.getByRole("checkbox").check();
  await page.locator('input[type="file"]').setInputFiles({ name: "synthetic.png", mimeType: "image/png", buffer: Buffer.from("synthetic") });
  const upload = page.waitForRequest((request) => request.url().endsWith("/api/v1/teacher/photos") && request.method() === "POST");
  await page.getByRole("button", { name: "Загрузить синтетическое фото" }).click();
  await upload;
});

test("teacher empty assignment state remains usable", async ({ page }) => {
  await page.route("**/api/v1/teacher/today", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ date: "2026-09-30", groups: [], schedule: [], attendance: [], tasks: [], notifications: [], unread_communication_count: 0 }) }));
  await page.goto("/teacher");
  await expect(page.getByText("0", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Назначенные" })).toBeVisible();
});
