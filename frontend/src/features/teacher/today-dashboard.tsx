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
  useEffect(() => { teacherApi.today().then(setData).catch((reason) => setError(userMessage(reason))); }, []);

  return <TeacherPageFrame title="Кабинет воспитателя" eyebrow="Сегодня">
    {error && <p className={styles.error}>{error}</p>}
    {!data && !error && <p className={styles.muted}>Загружаем рабочий день…</p>}
    {data && <>
      <div className={styles.grid}>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/groups">
          <h2>Мои группы</h2><div className={styles.metric}>{data.groups.length}</div><small>Открыть группы →</small>
        </Link>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/schedule">
          <h2>Расписание</h2><div className={styles.metric}>{data.schedule.length}</div><small>Посмотреть сегодня →</small>
        </Link>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/communications">
          <h2>Новые сообщения</h2><div className={styles.metric}>{data.unread_communication_count}</div><small>Открыть диалоги →</small>
        </Link>
        <Link className={`${styles.card} ${styles.actionCard}`} href="/teacher/more">
          <h2>Активные задачи</h2><div className={styles.metric}>{data.tasks.length}</div><small>Задачи и уведомления →</small>
        </Link>
      </div>
      <section className={styles.card}>
        <h2>Посещаемость по группам</h2>
        {data.attendance.length === 0
          ? <p className={styles.muted}>Нет групп для ежедневной отметки.</p>
          : <ul className={styles.list}>{data.attendance.map((item) => <li className={styles.row} key={item.group_id}>
              <strong>{data.groups.find((group) => group.id === item.group_id)?.name ?? "Группа"}</strong>
              <span>В саду: {item.on_site} · Ушли: {item.departed} · Отсутствуют: {item.absent} · Без отметки: {item.unknown}{item.needs_arrival ? ` · Уточнить приход: ${item.needs_arrival}` : ""} · Посещали: {item.present}</span>
            </li>)}</ul>}
      </section>
    </>}
  </TeacherPageFrame>;
}
