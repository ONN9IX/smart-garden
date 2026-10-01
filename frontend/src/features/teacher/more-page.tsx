"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { featureEnabled, type ProductFeature } from "@/config/product-features";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { Notification, TeacherTask } from "@/types/teacher";
import { styles, TeacherPageFrame } from "./shared";

type MoreLink = readonly [href: string, label: string, feature?: ProductFeature];

export function MorePage() {
  const [tasks, setTasks] = useState<TeacherTask[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(() => Promise.all([teacherApi.tasks(), teacherApi.notifications()])
    .then(([nextTasks, nextNotifications]) => { setTasks(nextTasks); setNotifications(nextNotifications); })
    .catch((reason) => setError(userMessage(reason))), []);
  useEffect(() => { void load(); }, [load]);

  const links: readonly MoreLink[] = [
    ["/teacher/announcements", "Объявления"],
    ["/teacher/diary", "Дневник", "diary"],
    ["/teacher/polls", "Опросы", "polls"],
    ["/teacher/incidents", "События", "incidents"],
    ["/teacher/photos", "Фото", "photos"],
  ];

  return <TeacherPageFrame title="Ещё" eyebrow="Рабочие разделы">
    {error && <p className={styles.error}>{error}</p>}
    <nav className={styles.tabs}>{links.filter(([, , feature]) => !feature || featureEnabled(feature)).map(([href, label]) => <Link key={href} href={href}>{label}</Link>)}</nav>
    <div className={styles.grid}>
      <section className={styles.card}><h2>Мои задачи</h2><ul className={styles.list}>{tasks.map((task) => <li className={styles.row} key={task.id}><span><strong>{task.title}</strong><br/><small>{task.description}</small></span><select value={task.status} disabled={task.status === "cancelled"} onChange={(event) => void teacherApi.updateTask(task.id, event.target.value as "open" | "in_progress" | "done").then(load)}><option value="open">Открыта</option><option value="in_progress">В работе</option><option value="done">Готово</option>{task.status === "cancelled" && <option value="cancelled">Отменена</option>}</select></li>)}</ul></section>
      <section className={styles.card}><h2>Уведомления</h2><ul className={styles.list}>{notifications.map((item) => <li className={styles.row} key={item.id}><span>{item.kind}</span>{!item.read_at && <button className={styles.buttonSecondary} onClick={() => void teacherApi.readNotification(item.id).then(load)}>Прочитано</button>}</li>)}</ul></section>
    </div>
  </TeacherPageFrame>;
}
