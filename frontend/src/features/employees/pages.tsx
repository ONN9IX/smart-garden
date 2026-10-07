"use client";

/** Employee list and profile keep contact values in memory and expose access by current role only. */
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { employeesApi } from "@/lib/api/employees";
import { managementPeopleApi } from "@/lib/api/management-people";
import { userMessage } from "@/lib/api/client";
import { fullName } from "@/lib/people-names";
import type { DuplicateMatch } from "@/types/people";
import type { Employee, EmployeeCategory, EmployeeFields, EmployeeSummary, InvitationResult } from "@/types/stage3";

const CATEGORY_LABELS: Record<EmployeeCategory, string> = {
  teacher: "Воспитатель",
  administrator: "Администратор",
  other: "Прочий сотрудник",
};
const TABS: Array<{ label: string; category?: EmployeeCategory; status: "active" | "archived" }> = [
  { label: "Воспитатели", category: "teacher", status: "active" },
  { label: "Администраторы", category: "administrator", status: "active" },
  { label: "Прочие сотрудники", category: "other", status: "active" },
  { label: "Архив", status: "archived" },
];
const empty: EmployeeFields = {
  first_name: "", last_name: "", middle_name: null, position: "", category: "other", phone: null, email: null,
};

function EmployeeForm({ initial = empty, busy, submit, cancel }: {
  initial?: EmployeeFields;
  busy: boolean;
  submit: (fields: EmployeeFields) => Promise<void>;
  cancel?: () => void;
}) {
  const [fields, setFields] = useState(initial);
  const submitting = useRef(false);
  function set<K extends keyof EmployeeFields>(key: K, value: EmployeeFields[K]) {
    setFields((current) => ({ ...current, [key]: value }));
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    try {
      await submit({
        ...fields,
        first_name: fields.first_name.trim(),
        last_name: fields.last_name.trim(),
        middle_name: fields.middle_name?.trim() || null,
        position: fields.position.trim(),
        phone: fields.phone?.trim() || null,
        email: fields.email?.trim() || null,
      });
    } finally { submitting.current = false; }
  }
  return <form className="card section-card" onSubmit={(event) => void save(event)}>
    <div className="form-grid">
      <label>Фамилия *<Input required maxLength={100} value={fields.last_name} onChange={(event) => set("last_name", event.target.value)} /></label>
      <label>Имя *<Input required maxLength={100} value={fields.first_name} onChange={(event) => set("first_name", event.target.value)} /></label>
      <label>Отчество<Input maxLength={100} value={fields.middle_name ?? ""} onChange={(event) => set("middle_name", event.target.value || null)} /></label>
      <label>Должность *<Input required maxLength={100} value={fields.position} onChange={(event) => set("position", event.target.value)} /></label>
      <label>Категория *<select className="input" required value={fields.category} onChange={(event) => set("category", event.target.value as EmployeeCategory)}>
        <option value="teacher">Воспитатель</option><option value="administrator">Администратор</option><option value="other">Прочий сотрудник</option>
      </select></label>
      <label>Телефон<Input type="tel" maxLength={32} value={fields.phone ?? ""} onChange={(event) => set("phone", event.target.value || null)} /></label>
      <label>Email<Input type="email" maxLength={254} value={fields.email ?? ""} onChange={(event) => set("email", event.target.value || null)} /></label>
    </div>
    <div className="action-row"><Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</Button>{cancel && <Button type="button" variant="secondary" onClick={cancel}>Отмена</Button>}</div>
  </form>;
}

export function EmployeesPage() { return <AuthGate route="dashboard"><EmployeesContent /></AuthGate>; }
function EmployeesContent() {
  const [tab, setTab] = useState(0);
  const [items, setItems] = useState<EmployeeSummary[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const activeTab = TABS[tab];
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setItems((await employeesApi.list({ status: activeTab.status, category: activeTab.category, q: search.trim() || undefined })).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [activeTab, search]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  return <AppShell><div className="page-heading"><span className="eyebrow">Люди и группы</span><h1>Сотрудники</h1><p>Категория сотрудника не меняет права его учётной записи.</p><Link className="button button-primary" href="/employees/new">Добавить сотрудника</Link></div>
    <div className="people-tabs" role="tablist" aria-label="Категории сотрудников">{TABS.map((item, index) => <button key={item.label} role="tab" aria-selected={tab === index} className={tab === index ? "people-tab people-tab-active" : "people-tab"} onClick={() => setTab(index)}>{item.label}</button>)}</div>
    <div className="filter-row"><label>Поиск по ФИО, должности или контактам<Input value={search} onChange={(event) => setSearch(event.target.value)} /></label></div>
    {error && <Alert>{error}</Alert>}{loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : items.length === 0 ? <p className="empty-state">{search ? "Сотрудники не найдены. Измените поиск." : tab === 3 ? "В архиве пока нет сотрудников." : "В этой категории пока нет сотрудников. Добавьте первую карточку."}</p> :
      <ul className="record-list">{items.map((item) => <li key={item.id}><Link className="record-link" href={`/employees/${item.id}`}><strong>{fullName(item)}</strong><span className="muted">{item.position} · {CATEGORY_LABELS[item.category]} · {item.account ? `${item.account.role === "TEACHER" ? "Доступ воспитателя" : "Доступ администратора"}: ${item.account.status === "active" ? "активен" : "заблокирован"}` : "Без аккаунта"}</span><span className="muted">{[item.phone, item.email].filter(Boolean).join(" · ") || "Контакты не указаны"}</span></Link></li>)}</ul>}
  </AppShell>;
}

export function NewEmployeePage() { return <AuthGate route="dashboard"><NewEmployeeContent /></AuthGate>; }
function NewEmployeeContent() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [duplicates, setDuplicates] = useState<DuplicateMatch[]>([]);
  const [pending, setPending] = useState<EmployeeFields | null>(null);
  async function create(fields: EmployeeFields) {
    setBusy(true); setError(""); setDuplicates([]); setPending(null);
    try {
      const result = await managementPeopleApi.checkDuplicates({
        kind: "employee", first_name: fields.first_name, last_name: fields.last_name,
        middle_name: fields.middle_name, phone: fields.phone, email: fields.email,
      });
      if (result.matches.length) { setDuplicates(result.matches); setPending(fields); return; }
      const item = await employeesApi.create(fields);
      router.push(`/employees/${item.id}`);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  async function continueCreate() {
    if (!pending) return;
    setBusy(true); setError("");
    try { const item = await employeesApi.create(pending); router.push(`/employees/${item.id}`); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <AppShell><Link className="text-link" href="/employees">← К сотрудникам</Link><div className="page-heading section-space"><h1>Добавить сотрудника</h1></div>{error && <Alert>{error}</Alert>}
    {duplicates.length > 0 && <section className="card section-card duplicate-warning"><h2>Проверьте похожие карточки</h2><p>Совпадение не объединяет записи. Откройте существующий профиль или подтвердите создание отдельной карточки.</p><ul>{duplicates.map((match) => <li key={match.id}><Link className="text-link" href={`/employees/${match.id}`}>{match.full_name}</Link>{match.context && <span> · {match.context}</span>}</li>)}</ul><Button disabled={busy} onClick={() => void continueCreate()}>Создать отдельную карточку</Button></section>}
    <EmployeeForm busy={busy} submit={create} /></AppShell>;
}

export function EmployeeDetailPage({ id }: { id: string }) { return <AuthGate route="dashboard"><EmployeeDetail id={id} /></AuthGate>; }
function EmployeeDetail({ id }: { id: string }) {
  const { current } = useAuth();
  const director = current?.user.role === "DIRECTOR";
  const [item, setItem] = useState<Employee | null>(null);
  const [profile, setProfile] = useState<Awaited<ReturnType<typeof managementPeopleApi.employeeProfile>> | null>(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const [employee, aggregate] = await Promise.all([employeesApi.get(id), managementPeopleApi.employeeProfile(id)]); setItem(employee); setProfile(aggregate); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function change(operation: () => Promise<Employee>, success: string): Promise<boolean> {
    setBusy(true); setError(""); setMessage("");
    try { setItem(await operation()); setMessage(success); return true; }
    catch (reason) { setError(userMessage(reason)); return false; }
    finally { setBusy(false); }
  }
  async function inviteAccount(operation: () => Promise<InvitationResult>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { const result = await operation(); setMessage(result.status === "sent" ? `${success} Логин: ${result.username}` : "Доступ сохранён, но письмо отправить не удалось."); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  async function updateAccount(operation: () => Promise<NonNullable<Employee["account"]>>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { const result = await operation(); setItem((currentItem) => currentItem && { ...currentItem, account: result }); setMessage(success); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  const teacher = item?.category === "teacher";
  const teacherAccount = item?.account?.role === "TEACHER";
  const hasAccountActions = director && item && item.status === "active" && (Boolean(item.account) || teacher || item.category === "administrator");
  const accountInvite = teacher ? employeesApi.resendTeacherInvite : (employeeId: string) => employeesApi.resendInvite(employeeId, "ADMIN");
  const accountBlock = teacherAccount ? employeesApi.blockTeacherAccount : employeesApi.block;
  const accountUnblock = teacherAccount ? employeesApi.unblockTeacherAccount : employeesApi.unblock;

  async function changeStatus() {
    if (!item || busy) return;
    const archiveText = "Сотрудник попадёт в архив; активные назначения воспитателя будут архивированы; связанный аккаунт заблокируется и его сеансы будут завершены. Восстановление карточки не вернёт назначения и доступ автоматически.";
    const restoreText = "Восстановить только карточку сотрудника? Назначения останутся архивными, а аккаунт — заблокированным.";
    if (!window.confirm(item.status === "active" ? archiveText : restoreText)) return;
    const succeeded = await change(() => item.status === "active" ? employeesApi.archive(id) : employeesApi.restore(id), item.status === "active" ? "Карточка и активные назначения архивированы. Доступ заблокирован." : "Карточка восстановлена отдельно. Назначения и доступ нужно восстанавливать отдельно.");
    if (succeeded) await load();
  }

  return <AppShell><Link className="text-link" href="/employees">← К сотрудникам</Link>
    {loading ? <Loading /> : !item ? <div className="section-space"><Alert>{error || "Запись не найдена."}</Alert><Button variant="secondary" onClick={() => void load()}>Повторить</Button></div> : <>
      <div className="page-heading section-space"><span className="eyebrow">{CATEGORY_LABELS[item.category]} · {item.status === "active" ? "Активен" : "Архив"}</span><h1>{fullName(item)}</h1><p>{item.position}</p><div className="action-row"><Button variant="secondary" onClick={() => setEditing((value) => !value)}>{editing ? "Отмена" : "Изменить"}</Button><Button variant="secondary" disabled={busy} onClick={() => void changeStatus()}>{item.status === "active" ? "Архивировать сотрудника" : "Восстановить карточку"}</Button></div></div>
      {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
      {editing ? <EmployeeForm key={item.updated_at} initial={{ first_name: item.first_name, last_name: item.last_name, middle_name: item.middle_name, position: item.position, category: item.category, phone: item.phone, email: item.email }} busy={busy} submit={async (fields) => { if (await change(() => employeesApi.update(id, fields), "Карточка сотрудника сохранена.")) { setEditing(false); await load(); } }} cancel={() => setEditing(false)} /> : <>
        <section className="profile-section card"><h2>Основное</h2><dl className="profile-facts"><div><dt>ФИО</dt><dd>{fullName(item)}</dd></div><div><dt>Должность</dt><dd>{item.position}</dd></div><div><dt>Категория</dt><dd>{CATEGORY_LABELS[item.category]}</dd></div></dl></section>
        <section className="profile-section card"><h2>Контакты</h2><dl className="profile-facts"><div><dt>Телефон</dt><dd>{item.phone || "Не указан"}</dd></div><div><dt>Email</dt><dd>{item.email || "Не указан"}</dd></div></dl></section>
        <section className="profile-section card"><h2>Назначения</h2>{profile?.assignments.length ? <ul className="record-list">{profile.assignments.map((assignment) => <li key={assignment.group_id}><Link className="record-link" href={`/groups/${assignment.group_id}`}><strong>{assignment.group_name}</strong><span className="muted">{assignment.status === "active" ? "Активное назначение" : "В архиве"}</span></Link></li>)}</ul> : <p className="empty-state">Нет назначений. Назначение воспитателя создаётся отдельным действием.</p>}<div className="action-row"><Link className="button button-secondary" href="/teacher-management">К управлению воспитателями</Link></div></section>
        <section className="profile-section card"><h2>Задачи</h2><p>Открытые: {profile?.open_tasks ?? 0} · Просроченные: {profile?.overdue_tasks ?? 0}</p><Link className="text-link" href={`/tasks?assignee_employee_id=${encodeURIComponent(id)}`}>Открыть задачи</Link></section>
        <section className="profile-section card"><h2>Документы</h2><p>Документы будут доступны после подключения защищённого хранилища.</p></section>
        {item.account ? <section className="profile-section card"><h2>Аккаунт</h2><p>Тип: {item.account.role === "TEACHER" ? "Воспитатель" : "Администратор"} · Логин: <strong>{item.account.username}</strong> · {item.account.status === "active" ? "Активен" : "Заблокирован"}{item.account.must_change_password ? " · Требуется смена пароля" : ""}</p>{item.status === "active" && <p className="muted">Восстановление карточки не меняет состояние аккаунта.</p>}
        {hasAccountActions && <div className="action-row">{item.account.must_change_password && <Button variant="secondary" disabled={busy} onClick={() => void inviteAccount(() => accountInvite(id), "Приглашение отправлено.")}>Отправить приглашение снова</Button>}<Button variant="secondary" disabled={busy} onClick={() => { const blocking = item.account?.status === "active"; if (!blocking || window.confirm("Заблокировать аккаунт сотрудника и завершить все действующие сеансы?")) void updateAccount(() => blocking ? accountBlock(id) : accountUnblock(id), blocking ? "Доступ заблокирован." : "Доступ восстановлен отдельно."); }}>{item.account.status === "active" ? "Заблокировать" : "Разблокировать"}</Button>{director && <Button variant="secondary" disabled={busy} onClick={() => { const next = item.account?.role === "TEACHER" ? "ADMIN" : "TEACHER"; if (window.confirm(`Изменить роль на ${next}?`)) void employeesApi.changeRole(id, next).then(load); }}>Изменить роль</Button>}</div>}
        </section> : hasAccountActions && <section className="profile-section card"><h2>Аккаунт</h2><p>Пользователь задаст пароль по одноразовой ссылке из письма.</p><Button disabled={busy} onClick={() => void inviteAccount(() => employeesApi.createAccount(id, teacher ? "TEACHER" : "ADMIN"), "Приглашение отправлено.")}>Создать доступ</Button></section>}
        <section className="profile-section card"><h2>История</h2>{director ? <Link className="text-link" href="/audit">Открыть журнал действий</Link> : <p>Журнал действий доступен директору.</p>}</section>
      </>}
    </>}
  </AppShell>;
}
