"use client";

/** Attendance day view: filter choices come from the current date/group/status rows. */

import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { attendanceApi } from "@/lib/api/attendance";
import { dashboardApi } from "@/lib/api/dashboard";
import { groupsApi } from "@/lib/api/groups";
import { userMessage } from "@/lib/api/client";
import type { Group } from "@/types/stage2";
import type { AttendanceRow, AttendanceStatus } from "@/types/stage3";

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
const time = (value: string | null) => value?.slice(0, 5) ?? "";
const labels = { present: "В саду", absent: "Отсутствует", unknown: "Не отмечен" };
const displayDate = (value: string) => value.split("-").reverse().join(".");

export function AttendancePage() { return <AuthGate route="dashboard"><AttendanceContent /></AuthGate>; }
function AttendanceContent() {
  const [fallbackToday] = useState(localDate);
  const userChangedDay = useRef(false);
  const [gardenToday, setGardenToday] = useState(fallbackToday);
  const [day, setDay] = useState(fallbackToday);
  const [groupId, setGroupId] = useState(""); const [status, setStatus] = useState<AttendanceStatus | "all">("all"); const [childId, setChildId] = useState("");
  const [groups, setGroups] = useState<Group[]>([]); const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const request = useRef(0);
  function invalidate() { request.current += 1; setRows([]); setLoading(true); setError(""); }
  useEffect(() => {
    dashboardApi.summary().then((summary) => {
      setGardenToday(summary.date);
      if (!userChangedDay.current) setDay(summary.date);
    }).catch(() => undefined);
  }, []);
  const load = useCallback(async () => {
    if (!day) return;
    const currentRequest = ++request.current;
    setLoading(true); setError("");
    try {
      // Fetch the eligible set before applying the child selector, so it never traps the choice.
      const [result, groupList] = await Promise.all([attendanceApi.list(day, groupId), groupsApi.list("all")]);
      if (currentRequest !== request.current) return;
      setRows(result.items); setGroups(groupList.items);
    } catch (reason) { if (currentRequest === request.current) setError(userMessage(reason)); }
    finally { if (currentRequest === request.current) setLoading(false); }
  }, [day, groupId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const statusRows = status === "all" ? rows : rows.filter((row) => row.status === status);
  const visible = childId ? statusRows.filter((row) => row.child.id === childId) : statusRows;
  const counts = rows.reduce((total, row) => ({ ...total, [row.status]: total[row.status] + 1 }), { present: 0, absent: 0, unknown: 0 });
  return <AppShell><div className="page-heading"><span className="eyebrow">Учёт</span><h1>Посещаемость</h1><p>Ручные отметки детей за выбранный день.</p></div>
    <div className="filter-row"><label>Дата <Input type="date" value={day} max={gardenToday || undefined} onChange={(event) => { userChangedDay.current = true; invalidate(); setDay(event.target.value); setGroupId(""); setStatus("all"); setChildId(""); }} /><span className="muted">Выбрано: {displayDate(day)}</span></label><label>Группа <select className="input" value={groupId} onChange={(event) => { invalidate(); setGroupId(event.target.value); setChildId(""); }}><option value="">Все группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label><label>Статус <select className="input" value={status} onChange={(event) => { setStatus(event.target.value as typeof status); setChildId(""); }}><option value="all">Все</option><option value="present">В саду</option><option value="absent">Отсутствует</option><option value="unknown">Не отмечен</option></select></label><label>Ребёнок <select className="input" value={childId} onChange={(event) => setChildId(event.target.value)}><option value="">Все дети</option>{statusRows.map((row) => <option key={row.child.id} value={row.child.id}>{row.child.last_name} {row.child.first_name}</option>)}</select></label></div>
    {error && <Alert>{error}</Alert>}
    {!loading && !error && <section className="dashboard-grid" aria-label="Сводка посещаемости">
      <article className="card metric-card"><span>Всего</span><strong>{rows.length}</strong></article>
      <article className="card metric-card"><span>В саду</span><strong>{counts.present}</strong></article>
      <article className="card metric-card"><span>Отсутствуют</span><strong>{counts.absent}</strong></article>
      <article className="card metric-card"><span>Не отмечены</span><strong>{counts.unknown}</strong></article>
    </section>}
    {loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : visible.length === 0 ? <p className="empty-state">По выбранным фильтрам дети не найдены.</p> : <div className="attendance-list">{visible.map((row) => <AttendanceItem key={`${row.date}:${row.child.id}`} row={row} refresh={load} />)}</div>}
  </AppShell>;
}

function AttendanceItem({ row, refresh }: { row: AttendanceRow; refresh: () => Promise<void> }) {
  const [mark, setMark] = useState<AttendanceStatus>(row.status);
  const [arrival, setArrival] = useState(time(row.arrival_time)); const [departure, setDeparture] = useState(time(row.departure_time));
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (busy) return;
    if (mark === "present" && departure && (!arrival || departure < arrival)) { setError("Время ухода должно быть не раньше прихода."); return; }
    setBusy(true); setError(""); setMessage("");
    try { await attendanceApi.save({ child_id: row.child.id, date: row.date, status: mark, arrival_time: mark === "present" ? arrival || null : null, departure_time: mark === "present" ? departure || null : null }); setMessage("Отметка сохранена."); await refresh(); }
    catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  }
  return <form className="card section-card section-space" onSubmit={(event) => void save(event)}>
    <h2>{row.child.last_name} {row.child.first_name} {row.child.middle_name ?? ""}</h2><p><strong>{labels[row.status]}</strong> · {row.group.name}</p>{row.status === "present" && (row.arrival_time || row.departure_time) && <p className="muted">Время: {row.arrival_time ? time(row.arrival_time) : "—"}{row.departure_time ? `–${time(row.departure_time)}` : ""}</p>}
    {row.child.status === "archived" ? <p>Карточка в архиве. Сохранённая отметка доступна для просмотра.</p> : <><div className="form-grid"><label>Отметка состояния <select className="input" value={mark} onChange={(event) => { const next = event.target.value as AttendanceStatus; setMark(next); if (next !== "present") { setArrival(""); setDeparture(""); } }}><option value="unknown">Не отмечен</option><option value="present">В саду</option><option value="absent">Отсутствует</option></select></label>{mark === "present" && <><label>Приход (необязательно) <Input type="time" value={arrival} onChange={(event) => setArrival(event.target.value)} /></label><label>Уход (необязательно) <Input type="time" value={departure} onChange={(event) => setDeparture(event.target.value)} /></label></>}</div><Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить отметку"}</Button></>}
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
  </form>;
}
