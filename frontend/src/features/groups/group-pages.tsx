"use client";

/** Group roster and operational detail are served by aggregated management projections. */
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { groupsApi } from "@/lib/api/groups";
import { managementPeopleApi } from "@/lib/api/management-people";
import { ApiError, userMessage } from "@/lib/api/client";
import { childCompactName, fullName } from "@/lib/people-names";
import type { GroupOverview, GroupProfile } from "@/types/people";
import type { StatusFilter } from "@/types/stage2";

const WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];
const RELATIONS: Record<string, string> = { mother: "Мать", father: "Отец", legal_guardian: "Законный представитель", other: "Другой представитель" };

export function GroupsPage() { return <AuthGate route="dashboard"><GroupsContent /></AuthGate>; }
function GroupsContent() {
  const router = useRouter();
  const [status, setStatus] = useState<StatusFilter>("active");
  const [groups, setGroups] = useState<GroupOverview[]>([]);
  const [search, setSearch] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setGroups((await managementPeopleApi.groupOverviews(status)).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [status]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const normalizedSearch = search.trim().toLocaleLowerCase("ru");
  const visible = groups.filter((item) => `${item.group.name} ${item.active_teacher_names.join(" ")}`.toLocaleLowerCase("ru").includes(normalizedSearch));
  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true; setBusy(true); setError("");
    try { const group = await groupsApi.create(name.trim()); setName(""); router.push(`/groups/${group.id}`); }
    catch (reason) { setError(userMessage(reason)); }
    finally { submitting.current = false; setBusy(false); }
  }
  return <AppShell>
    <div className="page-heading"><span className="eyebrow">Люди и группы</span><h1>Группы</h1><p>Состав и текущее состояние работы групп.</p></div>
    <section className="card section-card"><h2>Создать группу</h2><form onSubmit={(event) => void create(event)} className="inline-form"><FormField id="group-name" label="Название группы"><Input id="group-name" maxLength={100} required value={name} onChange={(event) => setName(event.target.value)} /></FormField><Button type="submit" disabled={busy}>{busy ? "Сохранение..." : "Создать группу"}</Button></form></section>
    <section className="section-space"><div className="section-heading"><h2>Список групп</h2></div><div className="filter-row"><label>Показать <select className="input" value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}><option value="active">Активные</option><option value="archived">Архив</option><option value="all">Все</option></select></label><label>Поиск по группе или воспитателю<Input value={search} onChange={(event) => setSearch(event.target.value)} /></label></div>
      {error && <Alert>{error}</Alert>}{loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : visible.length === 0 ? <p className="empty-state">{search ? "Группы не найдены. Измените поиск." : "Создайте первую группу."}</p> : <ul className="record-list group-overview-list">{visible.map((item) => <li key={item.group.id}><Link href={`/groups/${item.group.id}`} className="record-link group-overview-card"><strong>{item.group.name}</strong><span className="muted">{item.group.status === "active" ? "Активна" : "В архиве"} · Детей: {item.active_children}</span><span className="muted">Сегодня: в саду {item.present} · отсутствуют {item.absent} · не отмечены {item.unknown}</span><span className="muted">Воспитатели: {item.active_teacher_names.join(", ") || "нет"}</span><span className="muted">Расписание: {item.has_active_weekly_schedule ? "есть" : "не задано"} · Задачи: {item.open_tasks} открытых / {item.overdue_tasks} просроченных</span>{(!item.active_teacher_names.length || !item.has_active_weekly_schedule || item.overdue_tasks > 0) && <span className="status-warning">Требует внимания</span>}</Link></li>)}</ul>}
    </section>
  </AppShell>;
}

export function GroupDetailPage({ id }: { id: string }) { return <AuthGate route="dashboard"><GroupDetail id={id} /></AuthGate>; }
function GroupDetail({ id }: { id: string }) {
  const [profile, setProfile] = useState<GroupProfile | null>(null);
  const [name, setName] = useState("");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const submitting = useRef(false);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const value = await managementPeopleApi.groupProfile(id); setProfile(value); setName(value.group.name); }
    catch (reason) { setError(reason instanceof ApiError && reason.status === 404 ? "Группа не найдена." : userMessage(reason)); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true; setBusy(true); setError(""); setMessage("");
    try { await groupsApi.update(id, name.trim()); setEditing(false); setMessage("Группа сохранена."); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); submitting.current = false; }
  }
  async function changeStatus() {
    if (!profile || busy) return;
    const group = profile.group;
    if (!window.confirm(group.status === "active" ? "Архивировать группу? В группе не должно оставаться активных детей." : "Восстановить группу?")) return;
    setBusy(true); setError(""); setMessage("");
    try { await (group.status === "active" ? groupsApi.archive(id) : groupsApi.restore(id)); setMessage(group.status === "active" ? "Группа архивирована." : "Группа восстановлена."); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <AppShell><Link href="/groups" className="text-link">← К группам</Link>
    {loading ? <div className="section-space"><Loading /></div> : !profile ? <div className="section-space"><Alert>{error || "Группа не найдена."}</Alert><Button variant="secondary" onClick={() => void load()}>Повторить</Button></div> : <>
      <div className="page-heading section-space"><span className="eyebrow">Группа · {profile.group.status === "active" ? "Активна" : "Архив"}</span><h1>{profile.group.name}</h1><p>{profile.active_children} детей · {profile.active_teacher_count} активных воспитателей · расписаний: {profile.active_schedule_count}</p><div className="action-row"><Button variant="secondary" onClick={() => setEditing((value) => !value)}>{editing ? "Отмена" : "Изменить группу"}</Button><Button variant="secondary" disabled={busy} onClick={() => void changeStatus()}>{profile.group.status === "active" ? "Архивировать" : "Восстановить"}</Button></div></div>
      {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
      {editing && <form className="card section-card" onSubmit={(event) => void save(event)}><FormField id="edit-group-name" label="Название группы"><Input id="edit-group-name" maxLength={100} required value={name} onChange={(event) => setName(event.target.value)} /></FormField><Button disabled={busy}>Сохранить</Button></form>}
      <nav className="profile-section-links" aria-label="Разделы группы">{[["overview", "Обзор"], ["children", "Дети"], ["employees", "Сотрудники"], ["parents", "Родители"], ["attendance", "Посещаемость"], ["schedule", "Расписание"], ["messages", "Сообщения"], ["announcements", "Объявления"], ["tasks", "Задачи"]].map(([target, label]) => <a key={target} href={`#group-${target}`}>{label}</a>)}</nav>
      <section id="group-overview" className="profile-section card"><h2>Обзор</h2><div className="metric-grid"><div><strong>{profile.active_children}</strong><span>Детей</span></div><div><strong>{profile.present}</strong><span>В саду</span></div><div><strong>{profile.absent}</strong><span>Отсутствуют</span></div><div><strong>{profile.unknown}</strong><span>Не отмечены</span></div></div><p>Активных воспитателей: {profile.active_teacher_count} · Представителей: {profile.parent_count}</p><p>Расписание: {profile.active_schedule_count ? `есть, ${profile.active_schedule_count} записей` : "не заполнено"}</p><p>Задачи: {profile.open_tasks} открытых · {profile.overdue_tasks} просроченных</p></section>
      <section id="group-children" className="profile-section card"><h2>Дети</h2>{profile.children.length ? <ul className="record-list">{profile.children.map((child) => <li key={child.id}><Link className="record-link" href={`/children/${child.id}`}><strong>{childCompactName(child)}</strong><span className="muted">{child.today_attendance === "present" ? "В саду" : child.today_attendance === "absent" ? "Отсутствует" : "Не отмечен"} · Представителей: {child.active_guardian_count}</span></Link></li>)}</ul> : <p className="empty-state">В группе пока нет активных детей.</p>}<Link className="text-link" href={`/children?group_id=${encodeURIComponent(id)}`}>Открыть список детей группы</Link></section>
      <section id="group-employees" className="profile-section card"><h2>Сотрудники</h2>{profile.employees.length ? <ul className="record-list">{profile.employees.map((employee) => <li key={employee.id}><Link className="record-link" href={`/employees/${employee.id}`}><strong>{fullName(employee)}</strong><span className="muted">{employee.position} · {employee.account_status === "active" ? "Доступ активен" : "Доступ заблокирован"}</span></Link></li>)}</ul> : <p className="empty-state">Нет активных назначенных воспитателей.</p>}<Link className="text-link" href="/teacher-management">Управление назначениями</Link></section>
      <section id="group-parents" className="profile-section card"><h2>Родители и представители</h2>{profile.parents.length ? <ul className="record-list">{profile.parents.map((parent, index) => <li key={`${parent.id}-${parent.child_id}-${index}`}><Link className="record-link" href={`/guardians/${parent.id}`}><strong>{fullName(parent)}</strong><span className="muted">{RELATIONS[parent.relation_type]} · ребёнок: {parent.child_name}</span><span className="muted">{[parent.phone, parent.email].filter(Boolean).join(" · ") || "Контакты не указаны"}</span></Link></li>)}</ul> : <p className="empty-state">Представители отображаются по активным связям с детьми группы.</p>}</section>
      <section id="group-attendance" className="profile-section card"><h2>Посещаемость</h2><p>Сегодня: в саду {profile.present} · отсутствуют {profile.absent} · не отмечены {profile.unknown}</p><Link className="text-link" href={`/attendance?group_id=${encodeURIComponent(id)}`}>Открыть посещаемость группы</Link></section>
      <section id="group-schedule" className="profile-section card"><h2>Расписание</h2>{profile.schedule.length ? <ul>{profile.schedule.map((item) => <li key={item.id}>{WEEKDAYS[item.weekday]} · {item.start_time.slice(0, 5)}–{item.end_time.slice(0, 5)} · {item.title}</li>)}</ul> : <p className="empty-state">Недельное расписание ещё не заполнено.</p>}<Link className="text-link" href={`/schedule?group_id=${encodeURIComponent(id)}`}>Открыть расписание группы</Link></section>
      <section id="group-messages" className="profile-section card"><h2>Сообщения</h2><Link className="text-link" href={`/communications?group_id=${encodeURIComponent(id)}`}>Открыть сообщения группы</Link></section>
      <section id="group-announcements" className="profile-section card"><h2>Объявления</h2><Link className="text-link" href={`/announcements?group_id=${encodeURIComponent(id)}`}>Открыть объявления группы</Link></section>
      <section id="group-tasks" className="profile-section card"><h2>Задачи</h2><p>Открытые: {profile.open_tasks} · Просроченные: {profile.overdue_tasks}</p><Link className="text-link" href={`/tasks?group_id=${encodeURIComponent(id)}`}>Открыть задачи группы</Link></section>
    </>}
  </AppShell>;
}
