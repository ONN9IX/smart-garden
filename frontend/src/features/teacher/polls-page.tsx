"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { Poll } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function PollsPage() {
  const { groups, groupId, setGroupId } = useGroups(); const [items, setItems] = useState<Poll[]>([]);
  const [question, setQuestion] = useState(""); const [options, setOptions] = useState("Да\nНет"); const [error, setError] = useState("");
  const load = useCallback(() => { if (groupId) teacherApi.polls(groupId).then(setItems).catch((reason) => setError(userMessage(reason))); }, [groupId]);
  useEffect(load, [load]);
  async function submit(event: FormEvent) { event.preventDefault(); try { await teacherApi.createPoll({ group_id: groupId, question, options: options.split("\n").map((item) => item.trim()).filter(Boolean) }); setQuestion(""); load(); } catch (reason) { setError(userMessage(reason)); } }
  return <TeacherPageFrame title="Опросы"><div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /></div>{error && <p className={styles.error}>{error}</p>}<section className={styles.card}><form className={styles.toolbar} onSubmit={(event) => void submit(event)}><label>Вопрос<input value={question} maxLength={500} onChange={(event) => setQuestion(event.target.value)} /></label><label>Варианты, по одному в строке<textarea value={options} onChange={(event) => setOptions(event.target.value)} /></label><button className={styles.button}>Создать опрос</button></form><ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><span><strong>{item.question}</strong><br/>{item.options.map((option) => option.label).join(" · ")}</span>{item.status === "active" && <button className={styles.buttonSecondary} onClick={() => void teacherApi.closePoll(item.id).then(load)}>Закрыть</button>}</li>)}</ul></section></TeacherPageFrame>;
}
