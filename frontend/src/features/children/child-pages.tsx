"use client";

/**
 * Child screens load tenant-scoped records through the backend.
 * No names, birth dates or contact details are persisted in browser storage or URL query.
 */
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
import { childrenApi } from "@/lib/api/children";
import { groupsApi } from "@/lib/api/groups";
import { ChildRelations } from "@/features/guardians/relation-controls";
import { ApiError, userMessage } from "@/lib/api/client";
import type { Child, ChildFields, ChildSummary, Group, StatusFilter } from "@/types/stage2";

function fullName(item: { last_name: string; first_name: string; middle_name: string | null }) {
  return [item.last_name, item.first_name, item.middle_name].filter(Boolean).join(" ");
}

function dateLabel(value: string) {
  const [year, month, day] = value.split("-");
  return `${day}.${month}.${year}`;
}

const emptyFields: ChildFields = { last_name: "", first_name: "", middle_name: null, birth_date: "", group_id: "" };

function ChildForm({ initial = emptyFields, groups, busy, submit, cancel }: {
  initial?: ChildFields;
  groups: Group[];
  busy: boolean;
  submit: (fields: ChildFields) => Promise<void>;
  cancel?: () => void;
}) {
  const [fields, setFields] = useState<ChildFields>(initial);
  const submitting = useRef(false);
  const activeGroups = groups.filter((group) => group.status === "active");
  function set<K extends keyof ChildFields>(key: K, value: ChildFields[K]) {
    setFields((previous) => ({ ...previous, [key]: value }));
  }
  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    try {
      await submit({
        first_name: fields.first_name.trim(),
        last_name: fields.last_name.trim(),
        middle_name: fields.middle_name?.trim() || null,
        group_id: fields.group_id,
        birth_date: fields.birth_date,
      });
    } finally {
      submitting.current = false;
    }
  }
  return <form onSubmit={(event) => void onSubmit(event)} className="card section-card">
    <div className="form-grid">
      <FormField id="child-last-name" label="Фамилия"><Input id="child-last-name" required maxLength={100} value={fields.last_name} onChange={(event) => set("last_name", event.target.value)} /></FormField>
      <FormField id="child-first-name" label="Имя"><Input id="child-first-name" required maxLength={100} value={fields.first_name} onChange={(event) => set("first_name", event.target.value)} /></FormField>
      <FormField id="child-middle-name" label="Отчество (необязательно)"><Input id="child-middle-name" maxLength={100} value={fields.middle_name ?? ""} onChange={(event) => set("middle_name", event.target.value)} /></FormField>
      <FormField id="child-birth-date" label="Дата рождения"><Input id="child-birth-date" type="date" required value={fields.birth_date} onChange={(event) => set("birth_date", event.target.value)} /></FormField>
      <FormField id="child-group" label="Группа"><select className="input" id="child-group" required value={fields.group_id} onChange={(event) => set("group_id", event.target.value)}><option value="">Выберите группу</option>{activeGroups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></FormField>
    </div>
    {activeGroups.length === 0 && <p>Нет активных групп. <Link className="text-link" href="/groups">Сначала создайте группу</Link>.</p>}
    <div className="action-row"><Button type="submit" disabled={busy || activeGroups.length === 0}>{busy ? "Сохранение..." : "Сохранить"}</Button>{cancel && <Button type="button" variant="secondary" onClick={cancel}>Отмена</Button>}</div>
  </form>;
}

export function ChildrenPage() {
  return <AuthGate route="dashboard"><ChildrenContent /></AuthGate>;
}

function ChildrenContent() {
  const [items, setItems] = useState<ChildSummary[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [status, setStatus] = useState<StatusFilter>("active");
  const [groupId, setGroupId] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [children, groupList] = await Promise.all([childrenApi.list({ status, groupId: groupId || undefined }), groupsApi.list("all")]);
      setItems(children.items); setGroups(groupList.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [status, groupId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const visible = items.filter((child) => fullName(child).toLocaleLowerCase("ru").includes(search.trim().toLocaleLowerCase("ru")));
  return <AppShell>
    <div className="page-heading"><span className="eyebrow">Управление</span><h1>Дети</h1><p>Карточки детей вашего детского сада.</p><Link className="button button-primary" href="/children/new">Добавить ребёнка</Link></div>
    <div className="filter-row">
      <label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}><option value="active">Активные</option><option value="archived">Архив</option><option value="all">Все</option></select></label>
      <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Все группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Поиск по имени <Input value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    </div>
    {error && <Alert>{error}</Alert>}{loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : visible.length === 0 ? <p className="empty-state">Дети не найдены.</p> : <ul className="record-list">{visible.map((child) => <li key={child.id}><Link href={`/children/${child.id}`} className="record-link"><strong>{fullName(child)}</strong><span className="muted">{child.group.name} · {dateLabel(child.birth_date)} · {child.status === "active" ? "Активен" : "Архив"}</span></Link></li>)}</ul>}
  </AppShell>;
}

export function NewChildPage() {
  return <AuthGate route="dashboard"><NewChildContent /></AuthGate>;
}

function NewChildContent() {
  const router = useRouter();
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setGroups((await groupsApi.list()).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function create(fields: ChildFields) {
    setBusy(true); setError("");
    try { const child = await childrenApi.create(fields); router.push(`/children/${child.id}`); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <AppShell><Link className="text-link" href="/children">← К списку детей</Link><div className="page-heading section-space"><h1>Добавить ребёнка</h1></div>
    {error && <Alert>{error}</Alert>}
    {loading ? <Loading /> : error && groups.length === 0 ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : <ChildForm groups={groups} busy={busy} submit={create} />}
  </AppShell>;
}

export function ChildDetailPage({ id }: { id: string }) {
  return <AuthGate route="dashboard"><ChildDetail id={id} /></AuthGate>;
}

function ChildDetail({ id }: { id: string }) {
  const [child, setChild] = useState<Child | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [item, groupList] = await Promise.all([childrenApi.get(id), groupsApi.list("all")]);
      setChild(item); setGroups(groupList.items);
    } catch (reason) { setError(reason instanceof ApiError && reason.status === 404 ? "Запись не найдена." : userMessage(reason)); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function save(fields: ChildFields) {
    setBusy(true); setError(""); setMessage("");
    try { setChild(await childrenApi.update(id, fields)); setEditing(false); setMessage("Карточка сохранена."); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  async function changeStatus() {
    if (!child || busy) return;
    if (child.status === "active" && !window.confirm("Архивировать карточку ребёнка?")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      setChild(child.status === "active" ? await childrenApi.archive(id) : await childrenApi.restore(id));
      setMessage(child.status === "active" ? "Карточка архивирована." : "Карточка восстановлена.");
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <AppShell><Link className="text-link" href="/children">← К списку детей</Link>
    {loading ? <div className="section-space"><Loading /></div> : error && !child ? <div className="section-space"><Alert>{error}</Alert><Button variant="secondary" onClick={() => void load()}>Повторить</Button></div> : child && <>
      <div className="page-heading section-space"><span className="eyebrow">Ребёнок · {child.status === "active" ? "Активен" : "Архив"}</span><h1>{fullName(child)}</h1><p>Дата рождения: {dateLabel(child.birth_date)} · Группа: {child.group.name}</p></div>
      {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
      {editing ? <ChildForm key={child.updated_at} initial={{ first_name: child.first_name, last_name: child.last_name, middle_name: child.middle_name, birth_date: child.birth_date, group_id: child.group.id }} groups={groups} busy={busy} submit={save} cancel={() => setEditing(false)} /> : <div className="action-row"><Button variant="secondary" onClick={() => setEditing(true)}>Изменить</Button><Button variant="secondary" disabled={busy} onClick={() => void changeStatus()}>{child.status === "active" ? "Архивировать" : "Восстановить"}</Button></div>}
      <ChildRelations child={child} refresh={load} />
    </>}
  </AppShell>;
}
