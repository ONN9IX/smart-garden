"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { Today } from "@/types/teacher";
import { styles, TeacherPageFrame } from "./shared";

export function TodayDashboard() {
  const [data, setData] = useState<Today | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let version = 0;
    let active = true;
    const load = () => {
      const request = ++version;
      setData(null); setError("");
      teacherApi.today().then((value) => { if (active && request === version) setData(value); })
        .catch((reason) => { if (active && request === version) setError(userMessage(reason)); });
    };
    void Promise.resolve().then(() => { if (active) load(); });
    window.addEventListener("focus", load);
    return () => { active = false; version += 1; window.removeEventListener("focus", load); };
  }, [revision]);

  return <TeacherPageFrame title="Кабинет воспитателя" eyebrow="Сегодня">
    {error && <div><p className={styles.error} role="alert">{error}</p><button className={styles.buttonSecondary} onClick={() => setRevision((value) => value + 1)}>Повторить загрузку</button></div>}
    {!data && !error && <p className={styles.muted} role="status">Загружаем рабочий день…</p>}
    {data && <>
      <section className={`${styles.card} ${styles.stack}`}>
        <div className={styles.sectionHeading}><div><h2>Посещаемость по группам</h2><p className={styles.muted}>День сада: {data.date} · Только назначенные группы</p></div>
          <Link className={styles.button} href="/teacher/attendance">Отметить посещаемость</Link></div>
        {data.attendance.length === 0 ? <p className={styles.muted}>Нет групп для ежедневной отметки.</p>
          : <ul className={styles.list}>{data.attendance.map((item) => <li className={styles.row} key={item.group_id}>
            <div><strong>{data.groups.find((group) => group.id === item.group_id)?.name ?? "Группа"}</strong>
              <div className={styles.attendanceCounts}>
                <span>В саду: {item.on_site}</span><span>Ушли: {item.departed}</span><span>Отсутствуют: {item.absent}</span>
                <span className={item.unknown ? styles.attention : undefined}>Без отметки: {item.unknown}</span>
                <span className={item.needs_arrival ? styles.attention : undefined}>Уточнить приход: {item.needs_arrival}</span>
                <span>Посещали: {item.present}</span>
              </div></div>
          </li>)}</ul>}
      </section>
      <div className={styles.grid}>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/groups">
          <h2>Мои группы</h2><div className={styles.metric}>{data.groups.length}</div><small>Открыть группы →</small>
        </Link>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/schedule">
          <h2>Расписание</h2><div className={styles.metric}>{data.schedule.length}</div><small>Посмотреть сегодня →</small>
        </Link>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/communications">
          <h2>Сообщения</h2><div className={styles.metric}>{data.unread_communication_count}</div><small>Открыть диалоги →</small>
        </Link>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/more">
          <h2>Задачи</h2><div className={styles.metric}>{data.tasks.length}</div><small>Задачи и уведомления →</small>
        </Link>
      </div>

    </>}
  </TeacherPageFrame>;
}
