"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { groupsApi } from "@/lib/api/groups";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import { useUnsavedChanges } from "@/lib/use-unsaved-changes";
import type { Group } from "@/types/stage2";
import type { TeacherProjection, TeacherTask } from "@/types/management";
import { fullName, ManagerPage, useQueryParam } from "./common";

function taskStatusLabel(status: TeacherTask["status"]) {
  const labels: Record<TeacherTask["status"], string> = {
    open: "Открыта",
    in_progress: "В работе",
    done: "Готово",
    cancelled: "Отменена",
  };
  return labels[status];
}

function taskStatusClass(status: TeacherTask["status"]) {
  if (status === "open") return "status-chip status-chip-open";
  if (status === "in_progress") return "status-chip status-chip-progress";
  if (status === "done") return "status-chip status-chip-done";
  return "status-chip status-chip-cancelled";
}

export function TasksPage() {
  return <ManagerPage><TasksContent /></ManagerPage>;
}

function TasksContent() {
  const [teachers, setTeachers] = useState<TeacherProjection[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [items, setItems] = useState<TeacherTask[]>([]);
  const [employeeId, setEmployeeId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [status, setStatus] = useState("all");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const draftDirty = Boolean(title || description || dueAt);
  useUnsavedChanges(draftDirty);

  useQueryParam("group_id", setGroupId);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [teacherList, groupList, tasks] = await Promise.all([
        managementApi.teachers({ status: "active", account_status: "active" }),
        groupsApi.list("active"),
        managementApi.tasks({
          employee_id: employeeId || undefined,
          group_id: groupId || undefined,
          status,
        }),
      ]);
      setTeachers(teacherList.items);
      setGroups(groupList.items);
      setItems(tasks.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [employeeId, groupId, status]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!employeeId) return;
    setBusy(true); setError("");
    try {
      await managementApi.createTask({
        assignee_employee_id: employeeId,
        group_id: groupId || null,
        title: title.trim(),
        description: description.trim() || null,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      });
      setTitle(""); setDescription(""); setDueAt("");
      await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Управление</span><h1>Задачи воспитателей</h1><p>Назначение и контроль операционных задач.</p></div>
    <div className="filter-row">
      <label>Воспитатель <select className="input" value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}><option value="">Все</option>{teachers.map((item) => <option key={item.employee_id} value={item.employee_id}>{fullName(item)}</option>)}</select></label>
      <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Все</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">Все</option><option value="open">Открытые</option><option value="in_progress">В работе</option><option value="done">Готово</option><option value="cancelled">Отменено</option></select></label>
    </div>
    {error && <Alert>{error}</Alert>}
    <form className="card section-card" onSubmit={(event) => void create(event)}>
      <h2>Новая задача</h2>
      <div className="form-grid">
        <label>Воспитатель <select required className="input" value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}><option value="">Выберите</option>{teachers.map((item) => <option key={item.employee_id} value={item.employee_id}>{fullName(item)}</option>)}</select></label>
        <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Без группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
        <label>Срок <Input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} /></label>
        <label>Название <Input required maxLength={240} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      </div>
      <label>Описание<textarea className="input" rows={3} maxLength={4000} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <Button disabled={busy}>{busy ? "Создание..." : "Создать задачу"}</Button>
    </form>
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">Задач нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="card section-card">
      <h2>{item.title}</h2>
      {item.description && <p>{item.description}</p>}
      <p><span className={taskStatusClass(item.status)}>{taskStatusLabel(item.status)}</span>{item.due_at && <span className="muted"> · до {new Date(item.due_at).toLocaleString("ru-RU")}</span>}</p>
      {item.status !== "cancelled" && <div className="action-row">
        <select className="input compact-input" value={item.status} onChange={(event) => void managementApi.updateTask(item.id, { status: event.target.value as "open" | "in_progress" | "done" }).then(load).catch((reason) => setError(userMessage(reason)))}>
          <option value="open">Открыта</option><option value="in_progress">В работе</option><option value="done">Готово</option>
        </select>
        <Button variant="secondary" disabled={busy} onClick={() => {
          if (!window.confirm("Отменить задачу?")) return;
          void managementApi.cancelTask(item.id).then(load).catch((reason) => setError(userMessage(reason)));
        }}>Отменить</Button>
      </div>}
    </div></li>)}</ul>}
  </>;
}
