"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { AttendanceRow } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

function attendanceLabel(status: AttendanceRow["status"]) {
  if (status === "present") return "В детском саду";
  if (status === "absent") return "Отсутствует";
  return "Не отмечен";
}

function attendanceClass(status: AttendanceRow["status"]) {
  if (status === "present") return `${styles.statusPill} ${styles.statusPresent}`;
  if (status === "absent") return `${styles.statusPill} ${styles.statusAbsent}`;
  return `${styles.statusPill} ${styles.statusUnknown}`;
}

export function AttendancePage() {
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const userChangedDay = useRef(false);
  const [day, setDay] = useState("");
  const [today, setToday] = useState("");
  const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => {
    teacherApi.today().then((value) => { setToday(value.date); if (!userChangedDay.current) setDay(value.date); }).catch((reason) => setError(userMessage(reason)));
  }, []);
  const load = useCallback(() => {
    if (!groupId || !day) return;
    teacherApi.attendance(groupId, day).then(setRows).catch((reason) => setError(userMessage(reason)));
  }, [day, groupId]);
  useEffect(load, [load]);
  async function mark(row: AttendanceRow, status: AttendanceRow["status"]) {
    setBusy(row.child.id); setError("");
    try {
      await teacherApi.saveAttendance({ child_id: row.child.id, date: day, status });
      load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(""); }
  }
  async function markTime(row: AttendanceRow, action: "arrival" | "departure") {
    setBusy(row.child.id); setError("");
    try {
      await (action === "arrival" ? teacherApi.markArrival(row.child.id) : teacherApi.markDeparture(row.child.id));
      load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(""); }
  }
  return <TeacherPageFrame title="Посещаемость" eyebrow="Ежедневная отметка">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /><label>Дата<input type="date" value={day} onChange={(event) => { userChangedDay.current = true; setDay(event.target.value); }} /></label></div>
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    <section className={styles.card}><ul className={styles.list}>{rows.map((row) => <li className={styles.row} key={row.child.id}><span><strong>{row.child.first_name} {row.child.last_name}</strong><br/><span className={attendanceClass(row.status)}>{attendanceLabel(row.status)}</span>{row.arrival_time && <><br/><span className={styles.muted}>Пришёл: {row.arrival_time.slice(0, 5)}{row.departure_time ? ` · Ушёл: ${row.departure_time.slice(0, 5)}` : ""}</span></>}</span><span className={styles.toolbar}><button className={styles.button} disabled={day !== today || busy === row.child.id || Boolean(row.arrival_time)} onClick={() => void markTime(row, "arrival")}>Пришёл</button><button className={styles.buttonSecondary} disabled={day !== today || busy === row.child.id || !row.arrival_time || Boolean(row.departure_time)} onClick={() => void markTime(row, "departure")}>Ушёл</button><button className={styles.buttonSecondary} disabled={busy === row.child.id} onClick={() => void mark(row, "absent")}>Отсутствует</button></span></li>)}</ul>{rows.length === 0 && <p className={styles.muted}>Нет детей для отметки.</p>}</section>
  </TeacherPageFrame>;
}
