"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { ChildSummary, GuardianContext, Message, Thread } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function CommunicationsPage() {
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadId, setThreadId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [guardians, setGuardians] = useState<GuardianContext[]>([]);
  const [childId, setChildId] = useState("");
  const [guardianId, setGuardianId] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  const loadThreads = useCallback(() => teacherApi.threads().then((items) => {
    setThreads(items); setThreadId((current) => current || items[0]?.id || "");
  }).catch((reason) => setError(userMessage(reason))), []);
  useEffect(() => { void loadThreads(); }, [loadThreads]);
  useEffect(() => { if (threadId) teacherApi.messages(threadId).then(setMessages).catch((reason) => setError(userMessage(reason))); }, [threadId]);
  useEffect(() => { if (!groupId) return; Promise.all([teacherApi.children(groupId), teacherApi.guardians(groupId)]).then(([nextChildren, nextGuardians]) => {
    setChildren(nextChildren); setGuardians(nextGuardians); setChildId(nextChildren[0]?.id || "");
  }).catch((reason) => setError(userMessage(reason))); }, [groupId]);
  const selectedGuardianId = guardianId || guardians.find((item) => item.child_id === childId)?.id || "";
  async function openGroupThread() {
    if (!groupId) return;
    try { const thread = await teacherApi.groupThread(groupId); await loadThreads(); setThreadId(thread.id); }
    catch (reason) { setError(userMessage(reason)); }
  }
  async function openDirect() {
    if (!childId || !selectedGuardianId) return;
    try { const thread = await teacherApi.direct(childId, selectedGuardianId); await loadThreads(); setThreadId(thread.id); }
    catch (reason) { setError(userMessage(reason)); }
  }
  async function send(event: FormEvent) {
    event.preventDefault(); if (!threadId || !body.trim()) return;
    try { await teacherApi.sendMessage(threadId, body); setBody(""); setMessages(await teacherApi.messages(threadId)); }
    catch (reason) { setError(userMessage(reason)); }
  }
  return <TeacherPageFrame title="Родители и сообщения" eyebrow="Участники определяются сервером">
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    <section className={styles.card}><h2>Открыть диалог</h2><div className={styles.toolbar}>
      <GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} />
      <button className={styles.buttonSecondary} onClick={() => void openGroupThread()}>Чат группы</button>
      <label>Ребёнок<select value={childId} onChange={(event) => { setChildId(event.target.value); setGuardianId(""); }}>{children.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label>
      <label>Родитель<select value={selectedGuardianId} onChange={(event) => setGuardianId(event.target.value)}>{guardians.filter((item) => item.child_id === childId).map((guardian) => <option key={guardian.id} value={guardian.id}>{guardian.last_name} {guardian.first_name}</option>)}</select></label>
      <button className={styles.buttonSecondary} onClick={() => void openDirect()}>Личный диалог</button>
    </div></section>
    <div className={styles.grid}>
      <section className={styles.card}><h2>Диалоги</h2><ul className={styles.list}>{threads.map((thread) => <li key={thread.id}><button className={thread.id === threadId ? styles.button : styles.buttonSecondary} onClick={() => setThreadId(thread.id)}>{thread.thread_type === "group" ? "Группа" : "Личный диалог"}</button></li>)}</ul></section>
      <section className={styles.card}><h2>Сообщения</h2><ul className={styles.list}>{messages.map((message) => <li className={styles.row} key={message.id}><span>{message.body}</span><small>{new Date(message.created_at).toLocaleString("ru-RU")}</small></li>)}</ul><form className={styles.toolbar} onSubmit={(event) => void send(event)}><label>Новое сообщение<textarea value={body} maxLength={4000} onChange={(event) => setBody(event.target.value)} /></label><button className={styles.button} disabled={!threadId}>Отправить</button></form></section>
    </div>
  </TeacherPageFrame>;
}
