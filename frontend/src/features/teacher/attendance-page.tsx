"use client";

import { useCallback, useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { AttendanceRow } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function AttendancePage() {
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const [day, setDay] = useState("");
  const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => {
    teacherApi.today().then((value) => setDay(value.date)).catch((reason) => setError(userMessage(reason)));
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
  return <TeacherPageFrame title="Посещаемость" eyebrow="Ежедневная отметка">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /><label>Дата<input type="date" value={day} onChange={(event) => setDay(event.target.value)} /></label></div>
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    <section className={styles.card}><ul className={styles.list}>{rows.map((row) => <li className={styles.row} key={row.child.id}><span><strong>{row.child.first_name} {row.child.last_name}</strong><br/><small>Статус: {row.status}</small></span><span className={styles.toolbar}><button className={styles.button} disabled={busy === row.child.id} onClick={() => void mark(row, "present")}>Пришёл</button><button className={styles.buttonSecondary} disabled={busy === row.child.id} onClick={() => void mark(row, "absent")}>Отсутствует</button></span></li>)}</ul>{rows.length === 0 && <p className={styles.muted}>Нет детей для отметки.</p>}</section>
  </TeacherPageFrame>;
}
