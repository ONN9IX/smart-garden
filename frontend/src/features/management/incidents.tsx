"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { childrenApi } from "@/lib/api/children";
import { groupsApi } from "@/lib/api/groups";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { ChildSummary, Group } from "@/types/stage2";
import type { Incident } from "@/types/management";
import { fullName, ManagerPage, useQueryParam } from "./common";

export function IncidentsPage() {
  return <ManagerPage><IncidentsContent /></ManagerPage>;
}

function IncidentsContent() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [groupId, setGroupId] = useState("");
  const [childId, setChildId] = useState("");
  const [status, setStatus] = useState("all");
  const [items, setItems] = useState<Incident[]>([]);
  const [category, setCategory] = useState<Incident["category"]>("operational");
  const [occurredAt, setOccurredAt] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useQueryParam("group_id", setGroupId);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [groupList, childList, incidents] = await Promise.all([
        groupsApi.list("active"),
        childrenApi.list({ status: "active", groupId: groupId || undefined }),
        managementApi.incidents(groupId || undefined, status),
      ]);
      setGroups(groupList.items);
      setChildren(childList.items);
      setItems(incidents.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [groupId, status]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!groupId || !occurredAt) return;
    setBusy(true); setError("");
    try {
      await managementApi.createIncident({
        group_id: groupId,
        child_id: childId || null,
        occurred_at: new Date(occurredAt).toISOString(),
        category,
        description: description.trim(),
      });
      setDescription(""); setChildId(""); await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  async function edit(item: Incident) {
    const next = window.prompt("Описание происшествия", item.description);
    if (next == null || !next.trim()) return;
    setBusy(true); setError("");
    try { await managementApi.updateIncident(item.id, { description: next.trim() }); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Операции</span><h1>Происшествия</h1><p>Организационные и безопасностные события. Медицинские сведения здесь не ведутся.</p></div>
    <div className="filter-row">
      <label>Группа <select className="input" value={groupId} onChange={(event) => { setGroupId(event.target.value); setChildId(""); }}><option value="">Все группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">Все</option><option value="open">Открытые</option><option value="resolved">Решённые</option></select></label>
    </div>
    {error && <Alert>{error}</Alert>}
    <form className="card section-card" onSubmit={(event) => void create(event)}>
      <h2>Зафиксировать происшествие</h2>
      <div className="form-grid">
        <label>Группа <select required className="input" value={groupId} onChange={(event) => { setGroupId(event.target.value); setChildId(""); }}><option value="">Выберите</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
        <label>Ребёнок (необязательно) <select className="input" value={childId} onChange={(event) => setChildId(event.target.value)}><option value="">Без привязки</option>{children.map((child) => <option key={child.id} value={child.id}>{fullName(child)}</option>)}</select></label>
        <label>Дата и время <Input required type="datetime-local" value={occurredAt} onChange={(event) => setOccurredAt(event.target.value)} /></label>
        <label>Категория <select className="input" value={category} onChange={(event) => setCategory(event.target.value as Incident["category"])}><option value="safety">Безопасность</option><option value="behavior">Поведение</option><option value="operational">Организационное</option><option value="other">Другое</option></select></label>
      </div>
      <label>Описание<textarea required className="input" rows={4} maxLength={4000} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</Button>
    </form>
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">Происшествий нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="card section-card">
      <h2>{new Date(item.occurred_at).toLocaleString("ru-RU")} · {item.category}</h2>
      <p>{item.description}</p>
      <p className="muted">{item.status === "open" ? "Открыто" : "Решено"}</p>
      <div className="action-row"><Button variant="secondary" disabled={busy} onClick={() => void edit(item)}>Изменить описание</Button>{item.status === "open" && <Button variant="secondary" disabled={busy} onClick={() => void managementApi.updateIncident(item.id, { status: "resolved" }).then(load).catch((reason) => setError(userMessage(reason)))}>Отметить решённым</Button>}</div>
    </div></li>)}</ul>}
  </>;
}
