"use client";

import { useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { ScheduleItem } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

const weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];
export function SchedulePage() {
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { if (groupId) teacherApi.schedule(groupId).then(setItems).catch((reason) => setError(userMessage(reason))); }, [groupId]);
  return <TeacherPageFrame title="Расписание" eyebrow="Только чтение">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /></div>
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    <section className={styles.card}><ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><strong>{weekdays[item.weekday]} · {item.start_time.slice(0, 5)}–{item.end_time.slice(0, 5)}</strong><span>{item.title}</span></li>)}</ul>{items.length === 0 && <p className={styles.muted}>Расписание пока не заполнено.</p>}</section>
  </TeacherPageFrame>;
}
