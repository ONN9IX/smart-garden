"use client";

import { FormEvent, useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { ChildSummary, DiaryEntry } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function DiaryPage() {
  const { groups, groupId, setGroupId } = useGroups(); const [children, setChildren] = useState<ChildSummary[]>([]);
  const [childId, setChildId] = useState(""); const [entries, setEntries] = useState<DiaryEntry[]>([]);
  const [note, setNote] = useState(""); const [error, setError] = useState("");
  useEffect(() => { if (groupId) teacherApi.children(groupId).then((items) => { setChildren(items); setChildId(items[0]?.id || ""); }); }, [groupId]);
  useEffect(() => { if (childId) teacherApi.diary(childId).then(setEntries).catch((reason) => setError(userMessage(reason))); }, [childId]);
  async function submit(event: FormEvent) { event.preventDefault(); try { await teacherApi.createDiary({ child_id: childId, date: new Date().toISOString().slice(0, 10), note }); setNote(""); setEntries(await teacherApi.diary(childId)); } catch (reason) { setError(userMessage(reason)); } }
  return <TeacherPageFrame title="Дневник ребёнка"><div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /><label>Ребёнок<select value={childId} onChange={(event) => setChildId(event.target.value)}>{children.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label></div>{error && <p className={styles.error}>{error}</p>}<section className={styles.card}><form className={styles.toolbar} onSubmit={(event) => void submit(event)}><label>Запись<textarea value={note} maxLength={4000} onChange={(event) => setNote(event.target.value)} /></label><button className={styles.button} disabled={!childId || !note.trim()}>Сохранить</button></form><ul className={styles.list}>{entries.map((entry) => <li className={styles.row} key={entry.id}><span>{entry.note}</span><small>{entry.date}</small></li>)}</ul></section></TeacherPageFrame>;
}
