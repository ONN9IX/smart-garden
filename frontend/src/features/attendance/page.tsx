"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { attendanceApi } from "@/lib/api/attendance";
import { groupsApi } from "@/lib/api/groups";
import { userMessage } from "@/lib/api/client";
import type { Group } from "@/types/stage2";
import type { AttendanceRow, AttendanceStatus } from "@/types/stage3";

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
const time = (value: string | null) => value?.slice(0, 5) ?? "";
const labels = { present: "Присутствует", absent: "Отсутствует", unknown: "Без отметки" };

export function AttendancePage() { return <AuthGate route="dashboard"><AttendanceContent /></AuthGate>; }
function AttendanceContent() {
  const [day, setDay] = useState(localDate);
  const [groupId, setGroupId] = useState(""); const [status, setStatus] = useState<AttendanceStatus | "all">("all"); const [childId, setChildId] = useState("");
  const [groups, setGroups] = useState<Group[]>([]); const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const [result, groupList] = await Promise.all([attendanceApi.list(day, groupId, status, childId), groupsApi.list("all")]); setRows(result.items); setGroups(groupList.items); }
    catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); }
  }, [day, groupId, status, childId]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  return <AppShell><div className="page-heading"><span className="eyebrow">Учёт</span><h1>Посещаемость</h1><p>Ручные отметки детей за выбранный день.</p></div>
    <div className="filter-row"><label>Дата <Input type="date" value={day} max={localDate()} onChange={(event) => setDay(event.target.value)} /></label><label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Все группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label><label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="all">Все</option><option value="present">Присутствует</option><option value="absent">Отсутствует</option><option value="unknown">Без отметки</option></select></label><label>Ребёнок <select className="input" value={childId} onChange={(event) => setChildId(event.target.value)}><option value="">Все дети</option>{rows.map((row) => <option key={row.child.id} value={row.child.id}>{row.child.last_name} {row.child.first_name}</option>)}</select></label></div>
    {error && <Alert>{error}</Alert>}{loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : rows.length === 0 ? <p className="empty-state">На эту дату дети не найдены.</p> : <div className="attendance-list">{rows.map((row) => <AttendanceItem key={row.child.id} row={row} refresh={load} />)}</div>}
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
    <h2>{row.child.last_name} {row.child.first_name} {row.child.middle_name ?? ""}</h2><p>{row.group.name} · {labels[row.status]}{row.arrival_time ? ` · ${time(row.arrival_time)}` : ""}{row.departure_time ? `–${time(row.departure_time)}` : ""}</p>
    {row.child.status === "archived" ? <p>Карточка в архиве. Сохранённая отметка доступна для просмотра.</p> : <><div className="form-grid"><label>Отметка <select className="input" value={mark} onChange={(event) => { const next = event.target.value as AttendanceStatus; setMark(next); if (next !== "present") { setArrival(""); setDeparture(""); } }}><option value="unknown">Без отметки</option><option value="present">Присутствует</option><option value="absent">Отсутствует</option></select></label>{mark === "present" && <><label>Приход <Input type="time" value={arrival} onChange={(event) => setArrival(event.target.value)} /></label><label>Уход <Input type="time" value={departure} onChange={(event) => setDeparture(event.target.value)} /></label></>}</div><Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить отметку"}</Button></>}
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
  </form>;
}
