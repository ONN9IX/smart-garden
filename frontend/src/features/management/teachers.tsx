"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { useAuth } from "@/features/auth/auth-provider";
import { groupsApi } from "@/lib/api/groups";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { Group } from "@/types/stage2";
import type { TeacherProjection, TemporaryTeacherCredentials } from "@/types/management";
import { fullName, ManagerPage } from "./common";

export function TeachersPage() {
  return <ManagerPage><TeachersContent /></ManagerPage>;
}

function TeachersContent() {
  const { current } = useAuth();
  const director = current?.user.role === "DIRECTOR";
  const [items, setItems] = useState<TeacherProjection[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [status, setStatus] = useState("active");
  const [search, setSearch] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [groupId, setGroupId] = useState("");
  const [credentials, setCredentials] = useState<TemporaryTeacherCredentials | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [teachers, groupList] = await Promise.all([
        managementApi.teachers({ status, account_status: "all", q: search || undefined }),
        groupsApi.list("active"),
      ]);
      setItems(teachers.items);
      setGroups(groupList.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [search, status]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function run(operation: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setMessage(""); setCredentials(null);
    try { await operation(); setMessage(success); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  async function reveal(operation: () => Promise<TemporaryTeacherCredentials>, success: string) {
    setBusy(true); setError(""); setMessage(""); setCredentials(null);
    try { setCredentials(await operation()); setMessage(success); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  const assignable = items.filter((item) => item.account?.status === "active" && item.employee_status === "active");

  return <>
    <div className="page-heading"><span className="eyebrow">Управление</span><h1>Воспитатели</h1><p>Учётные записи воспитателей и назначения на группы.</p></div>
    <div className="filter-row">
      <label>Статус сотрудника <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}><option value="active">Активные</option><option value="archived">Архив</option><option value="all">Все</option></select></label>
      <label>Поиск <Input value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    </div>
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    {credentials && <section className="card section-card"><h2>Временные реквизиты</h2><p>Логин: <strong>{credentials.account.username}</strong></p><p>Временный пароль: <strong>{credentials.temporary_password}</strong></p><p>Сохраните и передайте безопасным способом. После закрытия этот пароль не восстанавливается.</p><Button variant="secondary" onClick={() => setCredentials(null)}>Скрыть пароль</Button></section>}
    {director && <section className="card section-card section-space"><h2>Назначить на группу</h2><div className="form-grid">
      <label>Воспитатель <select className="input" value={teacherId} onChange={(event) => setTeacherId(event.target.value)}><option value="">Выберите</option>{assignable.map((item) => <option key={item.employee_id} value={item.employee_id}>{fullName(item)}</option>)}</select></label>
      <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Выберите</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
    </div><Button disabled={busy || !teacherId || !groupId} onClick={() => void run(() => managementApi.createAssignment(teacherId, groupId), "Назначение создано.")}>Назначить</Button></section>}
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">Воспитатели и доступные кандидаты не найдены.</p> : <ul className="record-list">{items.map((item) => <li key={item.employee_id}><div className="card section-card">
      <h2>{fullName(item)}</h2><p className="muted">{item.position} · {item.employee_status === "active" ? "Активен" : "Архив"}</p>
      <p>{item.account ? "TEACHER: " + item.account.username + " · " + (item.account.status === "active" ? "активен" : "заблокирован") : "Учётная запись воспитателя не выдана"}</p>
      <div className="action-row">
        {director && item.eligible_for_teacher_account && <Button disabled={busy} onClick={() => void reveal(() => managementApi.createTeacherAccount(item.employee_id), "Доступ воспитателя выдан.")}>Выдать доступ</Button>}
        {director && item.account && <Button variant="secondary" disabled={busy} onClick={() => { if (window.confirm("Сбросить пароль воспитателя? Все действующие сеансы будут завершены.")) void reveal(() => managementApi.resetTeacherPassword(item.employee_id), "Временный пароль обновлён; старые сессии завершены."); }}>Сбросить пароль</Button>}
        {director && item.account && <Button variant="secondary" disabled={busy} onClick={() => { const blocking = item.account?.status === "active"; if (!blocking || window.confirm("Заблокировать аккаунт воспитателя? Все действующие сеансы будут завершены.")) void run(() => blocking ? managementApi.blockTeacher(item.employee_id) : managementApi.unblockTeacher(item.employee_id), blocking ? "Доступ заблокирован." : "Доступ восстановлен."); }}>{item.account.status === "active" ? "Заблокировать" : "Разблокировать"}</Button>}
      </div>
      <h3>Группы</h3>{item.assignments.length === 0 ? <p className="muted">Назначений нет.</p> : <ul>{item.assignments.map((assignment) => <li key={assignment.id}>{assignment.group_name} · {assignment.status === "active" ? "активно" : "архив"} {director && <Button variant="secondary" disabled={busy} onClick={() => {
        const restore = assignment.status !== "active";
        if (window.confirm(restore ? "Восстановить назначение?" : "Архивировать назначение?")) {
          void run(
            () => restore ? managementApi.restoreAssignment(assignment.id) : managementApi.archiveAssignment(assignment.id),
            restore ? "Назначение восстановлено." : "Назначение архивировано.",
          );
        }
      }}>{assignment.status === "active" ? "Архивировать" : "Восстановить"}</Button>}</li>)}</ul>}
    </div></li>)}</ul>}
  </>;
}
