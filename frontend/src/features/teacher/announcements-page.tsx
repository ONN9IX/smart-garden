"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { Announcement } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function AnnouncementsPage() {
  const { current } = useAuth();
  const { groups, groupId, setGroupId } = useGroups();
  const [items, setItems] = useState<Announcement[]>([]);
  const [editingId, setEditingId] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    if (!groupId) return;
    teacherApi.announcements(groupId).then(setItems).catch((reason) => setError(userMessage(reason)));
  }, [groupId]);
  useEffect(load, [load]);

  function clearForm() {
    setEditingId("");
    setTitle("");
    setBody("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      if (editingId) await teacherApi.updateAnnouncement(editingId, { title, body });
      else await teacherApi.createAnnouncement({ group_id: groupId, title, body });
      clearForm();
      load();
    } catch (reason) {
      setError(userMessage(reason));
    }
  }

  async function archive(id: string) {
    try {
      await teacherApi.archiveAnnouncement(id);
      if (editingId === id) clearForm();
      load();
    } catch (reason) {
      setError(userMessage(reason));
    }
  }

  return <TeacherPageFrame title="Объявления группы">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={(id) => { setGroupId(id); clearForm(); }} /></div>
    {error && <p className={styles.error}>{error}</p>}
    <section className={styles.card}>
      <form className={styles.toolbar} onSubmit={(event) => void submit(event)}>
        <label>Заголовок<input value={title} maxLength={120} onChange={(event) => setTitle(event.target.value)} /></label>
        <label>Текст<textarea value={body} maxLength={2000} onChange={(event) => setBody(event.target.value)} /></label>
        <button className={styles.button}>{editingId ? "Сохранить изменения" : "Опубликовать для группы"}</button>
        {editingId && <button type="button" className={styles.buttonSecondary} onClick={clearForm}>Отмена</button>}
      </form>
      <ul className={styles.list}>{items.map((item) => {
        const canManage = current?.user.id === item.created_by && item.status === "active";
        return <li className={styles.row} key={item.id}>
          <span><strong>{item.title}</strong><br/>{item.body}</span>
          <span><small>{item.status}</small>{canManage && <span className={styles.toolbar}>
            <button type="button" className={styles.buttonSecondary} onClick={() => { setEditingId(item.id); setTitle(item.title); setBody(item.body); }}>Изменить</button>
            <button type="button" className={styles.buttonSecondary} onClick={() => void archive(item.id)}>Архивировать</button>
          </span>}</span>
        </li>;
      })}</ul>
    </section>
  </TeacherPageFrame>;
}
