/** Stage 6 DIRECTOR/ADMIN cabinet frontend flow with synthetic API responses. */
import { expect, test, type Page, type Route } from "@playwright/test";

const cors = {
  "access-control-allow-origin": "http://localhost:3000",
  "access-control-allow-credentials": "true",
  "access-control-allow-methods": "GET,POST,PATCH,OPTIONS",
  "access-control-allow-headers": "content-type",
};

const groupId = "11111111-1111-4111-8111-111111111111";
const employeeId = "22222222-2222-4222-8222-222222222222";
const teacherUserId = "33333333-3333-4333-8333-333333333333";
const childId = "44444444-4444-4444-8444-444444444444";
const pollId = "55555555-5555-4555-8555-555555555555";
const incidentId = "66666666-6666-4666-8666-666666666666";
const taskId = "77777777-7777-4777-8777-777777777777";
const notificationId = "88888888-8888-4888-8888-888888888888";
const noticeId = "99999999-9999-4999-8999-999999999999";
const consentId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

const reply = (route: Route, body: object, status = 200) => route.fulfill({
  status,
  contentType: "application/json",
  headers: cors,
  body: JSON.stringify(body),
});

function group() {
  return { id: groupId, name: "Солнышко", status: "active", archived_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
}

function teacher() {
  return {
    employee_id: employeeId,
    first_name: "Анна",
    last_name: "Воспитатель",
    middle_name: null,
    position: "Воспитатель",
    employee_status: "active",
    account: { user_id: teacherUserId, username: "teacher-synthetic", status: "active", must_change_password: false },
    assignments: [{ id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", group_id: groupId, group_name: "Солнышко", status: "active" }],
    eligible_for_teacher_account: false,
  };
}

async function mockCabinet(page: Page, role: "DIRECTOR" | "ADMIN") {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    if (method === "OPTIONS") return route.fulfill({ status: 204, headers: cors });

    if (path.endsWith("/auth/me")) return reply(route, {
      user: { id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", username: role.toLowerCase() + "-synthetic", role, status: "active", must_change_password: false },
      organization: { id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", name: "Синтетический сад" },
    });
    if (path.endsWith("/dashboard/summary")) return reply(route, {
      date: "2026-10-01", active_children: 1, present: 1, on_site: 0, departed: 1, absent: 0, unknown: 0, needs_arrival: 0,
      active_groups: 1, active_employees: 1,
      groups: [{ id: groupId, name: "Солнышко", active_children: 1, present: 1, on_site: 0, departed: 1, absent: 0, unknown: 0, needs_arrival: 0 }],
    });
    if (path.endsWith("/management/today")) return reply(route, {
      date: "2026-10-01", active_children: 1, present: 1, on_site: 0, departed: 1, absent: 0, unknown: 0, needs_arrival: 0,
      active_groups: 1, active_employees: 1, groups_without_active_teacher_assignment: 0,
      open_tasks: 1, overdue_tasks: 0, open_incidents: 1, unread_notifications: 1,
      groups: [{ group_id: groupId, group_name: "Солнышко", active_children: 1, present: 1, on_site: 0, departed: 1, absent: 0, unknown: 0, needs_arrival: 0, has_active_teacher: true, has_active_weekly_schedule: true }],
      attention_items: [{ kind: "notifications_unread", entity_type: "notification", entity_id: notificationId, count: 1 }],
    });
    if (path.endsWith("/groups")) return reply(route, { items: [group()] });
    if (path.endsWith("/children")) return reply(route, { items: [{
      id: childId, first_name: "Ребёнок", last_name: "Синтетический", middle_name: null,
      birth_date: "2021-01-01", status: "active", group: { id: groupId, name: "Солнышко", status: "active" },
    }]});
    if (path.endsWith("/teacher-management/teachers")) return reply(route, { items: [teacher()] });
    if (path.includes("/teacher-management/teachers/")) return reply(route, teacher());
    if (path.endsWith("/teacher-management/assignments")) return reply(route, { items: teacher().assignments });

    if (path.endsWith("/teacher-management/schedule")) return reply(route, method === "GET" ? { items: [{
      id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", group_id: groupId, weekday: 1, start_time: "09:00:00",
      end_time: "10:00:00", title: "Музыка", status: "active",
      created_by: teacherUserId, updated_by: teacherUserId, created_at: "2026-10-01T08:00:00Z", updated_at: "2026-10-01T08:00:00Z",
    }]} : {});
    if (path.endsWith("/teacher-management/communications/groups/" + groupId + "/messages")) return reply(route, method === "GET" ? { items: [{
      id: "ffffffff-ffff-4fff-8fff-ffffffffffff", thread_id: "12121212-1212-4121-8121-121212121212",
      group_id: groupId, sender_user_id: teacherUserId, sender_role: "TEACHER", sender_name: "Воспитатель Анна", audience: "all", body: "Синтетическое сообщение", created_at: "2026-10-01T09:00:00Z",
    }]} : {});
    if (path.endsWith("/teacher-management/diary")) return reply(route, { items: [{
      id: "13131313-1313-4131-8131-131313131313", child_id: childId, group_id: groupId, date: "2026-10-01",
      author_user_id: teacherUserId, note: "Синтетическая запись", created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z",
    }]});
    if (path.endsWith("/teacher-management/polls")) return reply(route, { items: [{
      id: pollId, group_id: groupId, question: "Синтетический опрос", status: "active", closes_at: null,
      created_by: teacherUserId, created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z",
      options: [{ id: "14141414-1414-4141-8141-141414141414", label: "Да", sort_order: 0, vote_count: 2 }], total_votes: 2,
    }]});
    if (path.endsWith("/teacher-management/incidents")) return reply(route, { items: [{
      id: incidentId, group_id: groupId, child_id: childId, occurred_at: "2026-10-01T09:00:00Z",
      category: "operational", description: "Синтетическое происшествие", status: "open",
      reported_by: teacherUserId, resolved_by: null, created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z",
    }]});
    if (path.endsWith("/teacher-management/tasks")) return reply(route, { items: [{
      id: taskId, assignee_employee_id: employeeId, group_id: groupId, title: "Синтетическая задача",
      description: "Тест", due_at: "2026-10-02T09:00:00Z", status: "open",
      created_by: teacherUserId, created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z",
    }]});
    if (path.endsWith("/management/notifications")) return reply(route, { items: [{
      id: notificationId, kind: "task_attention", entity_type: "teacher_task", entity_id: taskId,
      read_at: null, created_at: "2026-10-01T09:00:00Z",
    }]});
    if (path.endsWith("/teacher-management/document-notices")) return reply(route, { items: [{
      id: noticeId, recipient_user_id: teacherUserId, title: "Политика", kind: "policy_update",
      requires_ack: true, issued_by: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      acknowledged_at: null, created_at: "2026-10-01T09:00:00Z",
    }]});
    if (path.endsWith("/teacher-management/photo-consents")) return reply(route, { items: [{
      id: consentId, child_id: childId, status: "granted", scope: "group_photo_report",
      effective_from: "2026-10-01T00:00:00Z", effective_to: null,
      recorded_by: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z",
    }]});
    if (path.endsWith("/management/settings")) {
      if (role === "ADMIN") return reply(route, { error: { code: "FORBIDDEN", message: "Доступ запрещён.", field: null } }, 403);
      return reply(route, { id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", name: "Синтетический сад", timezone: "Europe/Moscow" });
    }
    if (path.endsWith("/audit")) {
      if (role === "ADMIN") return reply(route, { error: { code: "FORBIDDEN", message: "Доступ запрещён.", field: null } }, 403);
      return reply(route, { items: [], limit: 50, offset: 0 });
    }
    return reply(route, { error: { code: "NOT_FOUND", message: "Запись не найдена.", field: null } }, 404);
  });
}

async function expectNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test("DIRECTOR can traverse the complete Stage 6 management cabinet", async ({ page }) => {
  await mockCabinet(page, "DIRECTOR");
  const routes: Array<[string, string]> = [
    ["/dashboard", "Сегодня"],
    ["/teachers", "Воспитатели"],
    ["/schedule", "Расписание"],
    ["/tasks", "Задачи воспитателей"],
    ["/communications?group_id=" + groupId, "Сообщения группы"],
    ["/notifications", "Уведомления"],
    ["/audit", "Журнал аудита"],
    ["/settings", "Настройки организации"],
  ];

  for (const [route, heading] of routes) {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Требует внимания" })).toBeVisible();
  await expect(page.locator(".today-group-counts dt").filter({ hasText: "Ушли" })).toBeVisible();
  await expect(page.getByText("1", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Задачи сада", { exact: true })).toBeVisible();

  await page.goto("/teachers");
  await expect(page.getByRole("button", { name: "Заблокировать" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Назначить" })).toBeVisible();

  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
  for (const viewport of [{ width: 1280, height: 900 }, { width: 768, height: 900 }, { width: 320, height: 780 }, { width: 360, height: 800 }, { width: 390, height: 844 }, { width: 430, height: 900 }]) {
    await page.setViewportSize(viewport);
    await page.goto("/notifications");
    await expectNoOverflow(page);
  }
});

test("ADMIN gets operations but no privileged teacher-account, assignment, Audit or Settings controls", async ({ page }) => {
  await mockCabinet(page, "ADMIN");

  await page.goto("/teachers");
  await expect(page.getByRole("heading", { name: "Воспитатели" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Сбросить пароль" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Заблокировать|Разблокировать/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Назначить" })).toHaveCount(0);

  for (const heading of ["Расписание", "Задачи воспитателей", "Уведомления"]) {
    const route = heading === "Расписание" ? "/schedule"
      : heading === "Задачи воспитателей" ? "/tasks"
      : "/notifications";
    await page.goto(route);
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }

  await page.goto("/dashboard");
  await expect(page.getByRole("link", { name: "Аудит" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Журнал действий" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Настройки" })).toHaveCount(0);

  await page.goto("/audit");
  await expect(page).toHaveURL(/\/403$/);
  await page.goto("/settings");
  await expect(page).toHaveURL(/\/403$/);

  expect(await page.evaluate(() => [localStorage.length, sessionStorage.length])).toEqual([0, 0]);
});
