"use client";

import { useCallback, useEffect, useState } from "react";
import { featureEnabled } from "@/config/product-features";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { DocumentNotice, Notification, TeacherTask } from "@/types/teacher";
import { styles, TeacherPageFrame } from "./shared";

function notificationLabel(item: Notification) {
  if (item.entity_type === "teacher_task") return "Задача требует внимания";
  if (item.entity_type.includes("communication") || item.entity_type.includes("message")) return "Новое сообщение";
  if (item.entity_type.includes("announcement")) return "Новое объявление";
  return "Новое уведомление";
}

export function MorePage() {
  const [tasks, setTasks] = useState<TeacherTask[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notices, setNotices] = useState<DocumentNotice[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(() => Promise.all([
    teacherApi.tasks(),
    teacherApi.notifications(),
    featureEnabled("documentNotices") ? teacherApi.notices() : Promise.resolve([] as DocumentNotice[]),
  ])
    .then(([nextTasks, nextNotifications, nextNotices]) => {
      setTasks(nextTasks);
      setNotifications(nextNotifications);
      setNotices(nextNotices);
    })
    .catch((reason) => setError(userMessage(reason))), []);
  useEffect(() => { void load(); }, [load]);

  return <TeacherPageFrame title="Задачи и уведомления" eyebrow="Рабочий день">
    {error && <p className={styles.error}>{error}</p>}
    <div className={styles.grid}>
      <section className={styles.card}>
        <h2>Мои задачи</h2>
        {tasks.length === 0 ? <p className={styles.muted}>Активных задач нет.</p> : <ul className={styles.list}>{tasks.map((task) => <li className={styles.row} key={task.id}>
          <span><strong>{task.title}</strong>{task.description && <><br/><small>{task.description}</small></>}</span>
          <select value={task.status} disabled={task.status === "cancelled"} onChange={(event) => void teacherApi.updateTask(task.id, event.target.value as "open" | "in_progress" | "done").then(load)}>
            <option value="open">Открыта</option><option value="in_progress">В работе</option><option value="done">Готово</option>{task.status === "cancelled" && <option value="cancelled">Отменена</option>}
          </select>
        </li>)}</ul>}
      </section>
      <section className={styles.card}>
        <h2>Уведомления</h2>
        {notifications.length === 0 ? <p className={styles.muted}>Новых уведомлений нет.</p> : <ul className={styles.list}>{notifications.map((item) => <li className={styles.row} key={item.id}>
          <span>{notificationLabel(item)}</span>
          {!item.read_at && <button className={styles.buttonSecondary} onClick={() => void teacherApi.readNotification(item.id).then(load)}>Отметить прочитанным</button>}
        </li>)}</ul>}
      </section>
      {featureEnabled("documentNotices") && <section className={styles.card}><h2>Документы к ознакомлению</h2><ul className={styles.list}>{notices.map((item) => <li className={styles.row} key={item.id}><span><strong>{item.title}</strong><br/><small>{item.kind}</small></span>{!item.acknowledged_at && <button className={styles.buttonSecondary} onClick={() => void teacherApi.acknowledgeNotice(item.id).then(load)}>Ознакомлен(а)</button>}</li>)}</ul></section>}
    </div>
  </TeacherPageFrame>;
}
