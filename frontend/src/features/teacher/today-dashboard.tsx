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
    {!data && !error && <p>Загружаем рабочий день…</p>}
    {data && <>
      <div className={styles.grid}>
        <section className={styles.card}><h2>Мои группы</h2><div className={styles.metric}>{data.groups.length}</div><Link href="/teacher/groups">Открыть группы</Link></section>
        <section className={styles.card}><h2>Расписание</h2><div className={styles.metric}>{data.schedule.length}</div><Link href="/teacher/schedule">На сегодня</Link></section>
        <section className={styles.card}><h2>Новые сообщения</h2><div className={styles.metric}>{data.unread_communication_count}</div><Link href="/teacher/communications">Открыть</Link></section>
        <section className={styles.card}><h2>Активные задачи</h2><div className={styles.metric}>{data.tasks.length}</div><Link href="/teacher/more">Подробнее</Link></section>
      </div>
      <section className={styles.card}><h2>Посещаемость</h2><ul className={styles.list}>{data.attendance.map((item) => <li className={styles.row} key={item.group_id}><span>{data.groups.find((group) => group.id === item.group_id)?.name ?? "Группа"}</span><span>Присутствуют: {item.present} · Отсутствуют: {item.absent} · Не отмечены: {item.unknown}</span></li>)}</ul></section>
    </>}
  </TeacherPageFrame>;
}
