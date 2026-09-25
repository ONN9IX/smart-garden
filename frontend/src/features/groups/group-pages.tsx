"use client";

/**
 * Group screens load only the current tenant's server-scoped data.
 * The backend decides archive eligibility and uniqueness.
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
import { ApiError, userMessage } from "@/lib/api/client";
import type { ChildSummary, Group, StatusFilter } from "@/types/stage2";

export function GroupsPage() {
  return <AuthGate route="dashboard"><GroupsContent /></AuthGate>;
}

function GroupsContent() {
  const router = useRouter();
  const [status, setStatus] = useState<StatusFilter>("active");
  const [groups, setGroups] = useState<Group[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const submitting = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setGroups((await groupsApi.list(status)).items);
    } catch (reason) {
      setError(userMessage(reason));
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const group = await groupsApi.create(name.trim());
      setName("");
      router.push(`/groups/${group.id}`);
    } catch (reason) {
      setError(userMessage(reason));
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return <AppShell>
    <div className="page-heading"><span className="eyebrow">Управление</span><h1>Группы</h1><p>Группы вашего детского сада.</p></div>
    <section className="card section-card"><h2>Создать группу</h2>
      <form onSubmit={(event) => void create(event)} className="inline-form">
        <FormField id="group-name" label="Название группы"><Input id="group-name" maxLength={100} required value={name} onChange={(event) => setName(event.target.value)} /></FormField>
        <Button type="submit" disabled={busy}>{busy ? "Сохранение..." : "Создать группу"}</Button>
      </form>
    </section>
    <section className="section-space"><div className="section-heading"><h2>Список групп</h2>
      <label>Показать <select className="input compact-input" value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}><option value="active">Активные</option><option value="archived">Архив</option></select></label>
    </div>
      {error && <Alert>{error}</Alert>}
      {loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : groups.length === 0
        ? <p className="empty-state">Групп пока нет.</p>
        : <ul className="record-list">{groups.map((group) => <li key={group.id}><Link href={`/groups/${group.id}`} className="record-link"><strong>{group.name}</strong><span className="muted">{group.status === "active" ? "Активна" : "В архиве"}</span></Link></li>)}</ul>}
    </section>
  </AppShell>;
}

export function GroupDetailPage({ id }: { id: string }) {
  return <AuthGate route="dashboard"><GroupDetail id={id} /></AuthGate>;
}

function GroupDetail({ id }: { id: string }) {
  const [group, setGroup] = useState<Group | null>(null);
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [name, setName] = useState("");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const submitting = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [item, childList] = await Promise.all([groupsApi.get(id), childrenApi.list({ groupId: id })]);
      setGroup(item);
      setName(item.name);
      setChildren(childList.items);
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 404 ? "Запись не найдена." : userMessage(reason));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      const updated = await groupsApi.update(id, name.trim());
      setGroup(updated);
      setEditing(false);
      setMessage("Группа сохранена.");
    } catch (reason) {
      setError(userMessage(reason));
    } finally {
      setBusy(false);
      submitting.current = false;
    }
  }

  async function changeStatus() {
    if (!group || busy) return;
    if (group.status === "active" && !window.confirm("Архивировать группу?")) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      setGroup(group.status === "active" ? await groupsApi.archive(id) : await groupsApi.restore(id));
      setMessage(group.status === "active" ? "Группа архивирована." : "Группа восстановлена.");
    } catch (reason) {
      setError(userMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return <AppShell><Link href="/groups" className="text-link">← К списку групп</Link>
    {loading ? <div className="section-space"><Loading /></div> : error && !group ? <div className="section-space"><Alert>{error}</Alert><Button variant="secondary" onClick={() => void load()}>Повторить</Button></div> : group && <>
      <div className="page-heading section-space"><span className="eyebrow">Группа · {group.status === "active" ? "Активна" : "Архив"}</span><h1>{group.name}</h1></div>
      {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
      <section className="card section-card">
        {editing ? <form onSubmit={(event) => void save(event)}><FormField id="edit-group-name" label="Название группы"><Input id="edit-group-name" maxLength={100} required value={name} onChange={(event) => setName(event.target.value)} /></FormField><div className="action-row"><Button disabled={busy} type="submit">Сохранить</Button><Button type="button" variant="secondary" onClick={() => { setEditing(false); setName(group.name); }}>Отмена</Button></div></form>
          : <div className="action-row"><Button variant="secondary" onClick={() => setEditing(true)}>Изменить название</Button><Button variant="secondary" disabled={busy} onClick={() => void changeStatus()}>{group.status === "active" ? "Архивировать" : "Восстановить"}</Button></div>}
      </section>
      <section className="section-space"><h2>Дети в группе</h2>{children.length ? <ul className="record-list">{children.map((child) => <li key={child.id}><Link className="record-link" href={`/children/${child.id}`}>{child.last_name} {child.first_name} {child.middle_name ?? ""}</Link></li>)}</ul> : <p className="empty-state">В группе нет активных детей.</p>}</section>
    </>}
  </AppShell>;
}
