"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { AttendanceRow } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

function rowState(row: AttendanceRow) {
  if (row.status === "absent") return "Отсутствует";
  if (row.status !== "present") return "Без отметки";
  if (row.departure_time) return "Ушёл";
  return row.arrival_time ? "В саду" : "Уточнить приход";
}

export function AttendancePage() {
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const userChangedDay = useRef(false);
  const requestId = useRef(0);
  const contextId = useRef(0);
  const inFlight = useRef(new Set<string>());
  const [day, setDay] = useState("");
  const [today, setToday] = useState("");
  const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<Set<string>>(() => new Set());
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    teacherApi.today().then((value) => { if (active) { setToday(value.date); if (!userChangedDay.current) setDay(value.date); } })
      .catch((reason) => { if (active) setError(userMessage(reason)); });
    return () => { active = false; };
  }, []);
  const load = useCallback(async () => {
    const request = ++requestId.current;
    if (!groupId || !day) { setRows([]); setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const result = await teacherApi.attendance(groupId, day);
      if (request === requestId.current) setRows(result);
    } catch (reason) {
      if (request === requestId.current) { setRows([]); setError(userMessage(reason)); }
      throw reason;
    } finally { if (request === requestId.current) setLoading(false); }
  }, [day, groupId]);
  useEffect(() => {
    void Promise.resolve().then(load).catch(() => undefined);
    return () => { requestId.current += 1; contextId.current += 1; };
  }, [load]);
  async function action(row: AttendanceRow, kind: "arrival" | "departure" | "absent") {
    const key = row.child.id;
    const contextAtStart = contextId.current;
    if (inFlight.current.has(key)) return;
    if (kind === "absent" && (row.arrival_time || row.departure_time) && !window.confirm("Исправить отметку на «Отсутствует» и очистить сохранённые времена прихода и ухода?")) return;
    inFlight.current.add(key); setBusy((current) => new Set(current).add(key)); setError("");
    try {
      if (kind === "absent") await teacherApi.saveAttendance({ child_id: key, date: day, status: "absent" });
      else await (kind === "arrival" ? teacherApi.markArrival(key) : teacherApi.markDeparture(key));
      if (contextId.current !== contextAtStart) return;
      await load();
    } catch (reason) {
      if (contextId.current !== contextAtStart) return;
      if (reason instanceof ApiError && [401, 403, 404].includes(reason.status)) {
        requestId.current += 1;
        setRows([]); setLoading(false);
      }
      setError(userMessage(reason));
    }
    finally { inFlight.current.delete(key); setBusy((current) => { const next = new Set(current); next.delete(key); return next; }); }
  }
  return <TeacherPageFrame title="Посещаемость" eyebrow="Ежедневная отметка">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={(id) => { requestId.current += 1; contextId.current += 1; setRows([]); setError(""); setGroupId(id); }} /><label>Дата<input type="date" value={day} onChange={(event) => { userChangedDay.current = true; requestId.current += 1; contextId.current += 1; setRows([]); setError(""); setDay(event.target.value); }} /></label></div>
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    {loading ? <p className={styles.muted}>Загружаем посещаемость…</p> : <section className={styles.card}><ul className={styles.list}>{rows.map((row) => {
      const state = rowState(row); const isBusy = busy.has(row.child.id);
      return <li className={styles.row} key={row.child.id}><span><strong>{row.child.first_name} {row.child.last_name}</strong><br/><span className={`${styles.statusPill} ${state === "В саду" ? styles.statusPresent : state === "Отсутствует" ? styles.statusAbsent : styles.statusUnknown}`}>{state}</span>{(row.arrival_time || row.departure_time) && <><br/><span className={styles.muted}>{row.arrival_time ? `Пришёл: ${row.arrival_time.slice(0, 5)}` : "Приход не отмечен"}{row.departure_time ? ` · Ушёл: ${row.departure_time.slice(0, 5)}` : ""}</span></>}</span><span className={styles.toolbar}>
        {state === "Без отметки" || state === "Отсутствует" || state === "Уточнить приход" ? <button className={styles.button} disabled={day !== today || isBusy} onClick={() => void action(row, "arrival")}>{isBusy ? "Сохранение…" : state === "Уточнить приход" ? "Записать приход" : "Пришёл"}</button> : null}
        {state === "В саду" ? <button className={styles.buttonSecondary} disabled={day !== today || isBusy} onClick={() => void action(row, "departure")}>{isBusy ? "Сохранение…" : "Ушёл"}</button> : null}
        {state !== "Отсутствует" && <button className={styles.buttonSecondary} disabled={isBusy} onClick={() => void action(row, "absent")}>{isBusy ? "Сохранение…" : "Отсутствует"}</button>}
      </span></li>;
    })}</ul>{!error && rows.length === 0 && <p className={styles.muted}>{groupId ? "Нет детей для отметки." : "Выберите назначенную группу."}</p>}</section>}
  </TeacherPageFrame>;
}
