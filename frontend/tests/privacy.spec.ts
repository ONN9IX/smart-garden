import { expect, test, type Page } from "@playwright/test";

const organization = { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", name: "Синтетическая организация", operating_profile: "KINDERGARTEN" };
const purpose = { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", code: "account_access", title: "Синтетический доступ", version: "synthetic-v1", legal_basis: "Синтетическое основание теста", ready: true, consent_required: false, subject_categories: ["user"], data_categories: ["Синтетические данные"], operations: ["Учёт"], access_roles: ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"], retention: "До конца теста", processors: null, locations: null };
const empty = { organization_id: organization.id, organization_name: organization.name, documents: [], purposes: [], operator_configured: false, real_pii_pilot: "NO-GO" };

async function mockPrivacy(page: Page, role: string, overview = empty) {
  await page.route("**/api/v1/auth/me", route => route.fulfill({ json: { user: { id: "self", username: "synthetic", role, status: "active", must_change_password: false }, organization } }));
  await page.route("**/api/v1/privacy/me", route => route.fulfill({ json: overview }));
  await page.route("**/api/v1/privacy/subjects", route => route.fulfill({ json: [{ label: "Мои данные", subject_user_id: "self", child_id: null, guardian_id: null }] }));
  await page.route("**/api/v1/privacy/consents", route => route.fulfill({ json: [] }));
  await page.route("**/api/v1/privacy/requests", route => route.fulfill({ json: [] }));
  await page.route("**/api/v1/privacy/operator/requests", route => route.fulfill({ json: [] }));
}

test("public privacy works without authorization and explains unpublished documents at 390px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/auth/me", route => route.abort("failed"));
  await page.route("**/api/v1/privacy/public/provider", route => route.fulfill({ json: { documents: [], real_pii_pilot: "NO-GO" } }));
  await page.goto("/privacy");
  await expect(page.getByRole("heading", { name: "Политика обработки персональных данных" })).toBeVisible();
  await expect(page.getByText(/Утверждённые действующие документы ещё не опубликованы/)).toBeVisible();
  await expect(page.getByText(/Техническая реализация не означает юридического одобрения/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("all pre-login data entry pages provide a privacy link without a consent checkbox", async ({ page }) => {
  await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 401, json: { error: { code: "UNAUTHORIZED", message: "Вход необходим" } } }));
  for (const path of ["/login", "/activate", "/forgot-password", "/reset-password", "/platform/login"]) {
    await page.goto(path);
    await expect(page.getByRole("link", { name: "Политика обработки персональных данных" })).toHaveAttribute("href", "/privacy");
    await expect(page.getByRole("checkbox")).toHaveCount(0);
  }
});

for (const role of ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"]) {
  test(`${role} can open own privacy workspace without consent on login`, async ({ page }) => {
    await mockPrivacy(page, role);
    await page.goto("/privacy-center");
    await expect(page.getByRole("heading", { name: "Конфиденциальность", exact: true })).toBeVisible();
    await expect(page.getByText("Юридические реквизиты оператора ещё не подтверждены.", { exact: false })).toBeVisible();
    await expect(page.getByRole("button", { name: "Зарегистрировать обращение" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Журнал обращений оператору" })).toHaveCount(role === "DIRECTOR" ? 1 : 0);
    await expect(page.getByRole("checkbox")).toHaveCount(0);
  });
}

test("parent request retries use the same key and do not send text or a tenant selector", async ({ page }) => {
  await mockPrivacy(page, "PARENT");
  const bodies: Record<string, unknown>[] = [];
  let stored: unknown[] = [];
  await page.route("**/api/v1/privacy/requests", async route => {
    if (route.request().method() === "GET") return route.fulfill({ json: stored });
    const payload = route.request().postDataJSON(); bodies.push(payload);
    if (bodies.length === 1) return route.abort("failed");
    stored = [{ id: "request-1", kind: payload.kind, child_id: null, requester_user_id: "self", status: "submitted", created_at: "2026-10-20T12:00:00Z", due_at: null, needs_deadline: true, overdue: false, history: [] }];
    return route.fulfill({ status: 201, json: stored[0] });
  });
  await page.goto("/privacy-center");
  await page.getByLabel("Тип обращения").selectOption("erasure");
  await page.getByRole("button", { name: "Зарегистрировать обращение" }).click();
  await expect(page.getByText(/Нет соединения с сервером/)).toBeVisible();
  await page.getByRole("button", { name: "Зарегистрировать обращение" }).click();
  await expect(page.getByText(/Обращение request-/)).toBeVisible();
  expect(bodies).toHaveLength(2); expect(bodies[0]).toEqual(bodies[1]);
  expect(Object.keys(bodies[0]).sort()).toEqual(["child_id", "idempotency_key", "kind"]);
  await expect(page.getByText("Оператору необходимо определить срок ответа.")).toBeVisible();
});

test("external-document attestation is explicit and remains separate from a subject consent", async ({ page }) => {
  await mockPrivacy(page, "DIRECTOR");
  await page.route("**/api/v1/privacy/me", route => route.fulfill({ json: { ...empty, purposes: [purpose] } }));
  const employee = { id: "e1", first_name: "Синтетический", last_name: "Педагог", middle_name: null, position: "Воспитатель", category: "teacher", phone: null, email: "synthetic@example.test", status: "active", account: null, archived_at: null, created_at: "2026-10-20T00:00:00Z", updated_at: "2026-10-20T00:00:00Z" };
  await page.route("**/api/v1/employees/e1", route => route.fulfill({ json: employee }));
  await page.route("**/api/v1/management/employees/e1/profile", route => route.fulfill({ json: { assignments: [], open_tasks: 0, overdue_tasks: 0 } }));
  let payload: unknown;
  await page.route("**/api/v1/privacy/attestations", route => { payload = route.request().postDataJSON(); return route.fulfill({ status: 201, json: { recorded: 1, is_subject_consent: false } }); });
  await page.goto("/employees/e1");
  const save = page.getByRole("button", { name: "Записать подтверждение документов" });
  await expect(save).toBeDisabled();
  await page.getByLabel("Правовое основание").selectOption(purpose.id);
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await page.getByRole("checkbox").check();
  await save.click();
  await expect(page.getByText(/Подтверждение записано/)).toBeVisible();
  expect(payload).toEqual({ profile_type: "employee", profile_ids: ["e1"], purpose_id: purpose.id, documents_confirmed: true });
  await expect(page.getByText(/а не согласие родителя и не электронная подпись/)).toBeVisible();
});

test("paper-original form requires both checks and withdrawal preserves its history", async ({ page }) => {
  await mockPrivacy(page, "DIRECTOR");
  const consentPurpose = { ...purpose, code: "family_contacts", title: "Синтетическая отдельная цель", consent_required: true, consent_document_id: "consent-doc-1" };
  await page.route("**/api/v1/privacy/me", route => route.fulfill({ json: { ...empty, purposes: [consentPurpose] } }));
  let rows: Record<string, unknown>[] = [];
  let savedPayload: Record<string, unknown> = {};
  await page.route("**/api/v1/privacy/consents", route => {
    if (route.request().method() === "GET") return route.fulfill({ json: rows });
    savedPayload = route.request().postDataJSON();
    rows = [{ ...savedPayload, id: "paper-1", purpose_title: consentPurpose.title, document_version: "synthetic-v1", document_hash: "a".repeat(64), recorded_by: "self", status: "recorded", current_version: true, history: [{ action: "recorded", at: "2026-10-20T12:00:00Z", actor_user_id: "self" }] }];
    return route.fulfill({ status: 201, json: rows[0] });
  });
  await page.route("**/api/v1/privacy/consents/paper-1/withdraw", route => {
    rows[0] = { ...rows[0], status: "withdrawn", history: [...rows[0].history as unknown[], { action: "withdrawn", at: "2026-10-21T12:00:00Z", actor_user_id: "self" }] };
    return route.fulfill({ json: rows[0] });
  });
  await page.goto("/privacy-center");
  await page.getByLabel("Цель согласия").selectOption(purpose.id);
  await page.getByLabel("Субъект и представитель").selectOption("self::");
  await page.getByLabel("Дата получения оригинала").fill("2026-10-20");
  const save = page.getByRole("button", { name: "Учесть оригинал", exact: true });
  await expect(save).toBeDisabled();
  await page.getByLabel("Бумажный оригинал получен", { exact: false }).check();
  await expect(save).toBeDisabled();
  await page.getByLabel("Я проверил полномочия", { exact: false }).check();
  await save.click();
  await expect(page.getByText(/Сведения об оригинале учтены/)).toBeVisible();
  expect(savedPayload.original_held_confirmed).toBe(true); expect(savedPayload.authority_confirmed).toBe(true);
  expect(savedPayload.document_id).toBe("consent-doc-1"); expect(savedPayload).not.toHaveProperty("organization_id");
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "Отозвать согласие" }).click();
  await expect(page.getByText(/Статус: Отозвано/)).toBeVisible();
  await page.getByText("История и версия", { exact: true }).click();
  await expect(page.getByText(/Отзыв зарегистрирован/)).toBeVisible();
  expect(rows).toHaveLength(1); expect(rows[0].history).toHaveLength(2);
});
