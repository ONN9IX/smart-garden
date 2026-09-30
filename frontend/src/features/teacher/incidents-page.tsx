"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { Incident } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function IncidentsPage() {
  const { groups, groupId, setGroupId } = useGroups(); const [items, setItems] = useState<Incident[]>([]);
  const [description, setDescription] = useState(""); const [category, setCategory] = useState<Incident["category"]>("operational"); const [error, setError] = useState("");
  const load = useCallback(() => { if (groupId) teacherApi.incidents(groupId).then(setItems).catch((reason) => setError(userMessage(reason))); }, [groupId]);
  useEffect(load, [load]);
  async function submit(event: FormEvent) { event.preventDefault(); try { await teacherApi.createIncident({ group_id: groupId, occurred_at: new Date().toISOString(), category, description }); setDescription(""); load(); } catch (reason) { setError(userMessage(reason)); } }
  return <TeacherPageFrame title="Рабочие события"><p className={styles.muted}>Только операционные события. Медицинские сведения здесь не хранятся.</p><div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /></div>{error && <p className={styles.error}>{error}</p>}<section className={styles.card}><form className={styles.toolbar} onSubmit={(event) => void submit(event)}><label>Категория<select value={category} onChange={(event) => setCategory(event.target.value as Incident["category"])}><option value="operational">Организационное</option><option value="safety">Безопасность</option><option value="behavior">Поведение</option><option value="other">Другое</option></select></label><label>Описание<textarea value={description} maxLength={4000} onChange={(event) => setDescription(event.target.value)} /></label><button className={styles.button}>Записать</button></form><ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><span>{item.description}<br/><small>{item.category}</small></span>{item.status === "open" && <button className={styles.buttonSecondary} onClick={() => void teacherApi.resolveIncident(item.id).then(load)}>Решено</button>}</li>)}</ul></section></TeacherPageFrame>;
}
