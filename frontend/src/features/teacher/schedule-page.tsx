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
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    let version = 0;
    const load = () => {
      const request = ++version;
      setItems([]); setError(""); setLoading(Boolean(groupId));
      if (!groupId) return;
      teacherApi.schedule(groupId).then((value) => { if (active && request === version) setItems(value); })
        .catch((reason) => { if (active && request === version) setError(userMessage(reason)); })
        .finally(() => { if (active && request === version) setLoading(false); });
    };
    void Promise.resolve().then(() => { if (active) load(); });
    window.addEventListener("focus", load);
    return () => { active = false; version += 1; window.removeEventListener("focus", load); };
  }, [groupId, revision]);
  return <TeacherPageFrame title="Расписание" eyebrow="Только чтение">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={(id) => { setItems([]); setError(""); setGroupId(id); }} /></div>
    {(error || groupError) && <p className={styles.error} role="alert">{error || groupError}</p>}
    {error && <button className={styles.buttonSecondary} onClick={() => setRevision((value) => value + 1)}>Повторить загрузку</button>}
    {loading && <p className={styles.muted} role="status">Загружаем данные группы…</p>}
    <section className={styles.card}><ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><strong>{weekdays[item.weekday]} · {item.start_time.slice(0, 5)}–{item.end_time.slice(0, 5)}</strong><span>{item.title}</span></li>)}</ul>{!loading && !error && items.length === 0 && <p className={styles.muted}>Расписание пока не заполнено.</p>}</section>
  </TeacherPageFrame>;
}
