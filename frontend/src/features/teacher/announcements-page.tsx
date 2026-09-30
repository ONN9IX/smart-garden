"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { Announcement } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function AnnouncementsPage() {
  const { groups, groupId, setGroupId } = useGroups(); const [items, setItems] = useState<Announcement[]>([]);
  const [title, setTitle] = useState(""); const [body, setBody] = useState(""); const [error, setError] = useState("");
  const load = useCallback(() => { if (groupId) teacherApi.announcements(groupId).then(setItems).catch((reason) => setError(userMessage(reason))); }, [groupId]);
  useEffect(load, [load]);
  async function submit(event: FormEvent) { event.preventDefault(); try { await teacherApi.createAnnouncement({ group_id: groupId, title, body }); setTitle(""); setBody(""); load(); } catch (reason) { setError(userMessage(reason)); } }
  return <TeacherPageFrame title="Объявления группы"><div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /></div>{error && <p className={styles.error}>{error}</p>}<section className={styles.card}><form className={styles.toolbar} onSubmit={(event) => void submit(event)}><label>Заголовок<input value={title} maxLength={120} onChange={(event) => setTitle(event.target.value)} /></label><label>Текст<textarea value={body} maxLength={2000} onChange={(event) => setBody(event.target.value)} /></label><button className={styles.button}>Опубликовать для группы</button></form><ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><span><strong>{item.title}</strong><br/>{item.body}</span><small>{item.status}</small></li>)}</ul></section></TeacherPageFrame>;
}
