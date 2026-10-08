"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { useAuth } from "@/features/auth/auth-provider";
import { communicationAudienceLabels, relationLabels } from "@/lib/presentation";
import { teacherApi } from "@/lib/api/teacher";
import type { ChildSummary, GuardianContext, Message, ThreadV2 } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function CommunicationsPage() {
  const { current } = useAuth();
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const [threads, setThreads] = useState<ThreadV2[]>([]);
  const [threadId, setThreadId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [guardians, setGuardians] = useState<GuardianContext[]>([]);
  const [childId, setChildId] = useState("");
  const [guardianId, setGuardianId] = useState("");
  const [body, setBody] = useState("");
  const [groupAudience, setGroupAudience] = useState<"all" | "teachers">("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const clientMessageId = useRef(crypto.randomUUID());
  const [tab, setTab] = useState<"all" | "direct" | "group" | "staff">("all");
  const loadThreads = useCallback(() => teacherApi.v2Threads().then((items) => {
    setThreads(items); setThreadId((selected) => selected || items[0]?.id || ""); setError("");
  }).catch((reason) => setError(userMessage(reason))), []);
  useEffect(() => { void loadThreads(); }, [loadThreads]);
  useEffect(() => { if (threadId) teacherApi.v2Messages(threadId).then(async (items) => {
    setMessages(items); setError("");
    const last = items.at(-1);
    if (last) { await teacherApi.v2MarkRead(threadId, last.id); await loadThreads(); }
  }).catch((reason) => setError(userMessage(reason))); }, [threadId, loadThreads]);
  useEffect(() => { if (!groupId) return; Promise.all([teacherApi.children(groupId), teacherApi.guardians(groupId)]).then(([nextChildren, nextGuardians]) => {
    setChildren(nextChildren); setGuardians(nextGuardians); setChildId(nextChildren[0]?.id || ""); setError("");
  }).catch((reason) => setError(userMessage(reason))); }, [groupId]);
  const selectedGuardianId = guardianId || guardians.find((item) => item.child_id === childId)?.id || "";
  const selectedGuardian = guardians.find((item) => item.id === selectedGuardianId);
  async function openGroupThread() {
    if (!groupId) return;
    try { const thread = await teacherApi.v2GroupThread(groupId, groupAudience); await loadThreads(); setThreadId(thread.id); setError(""); }
    catch (reason) { setError(userMessage(reason)); }
  }
  async function openDirect() {
    if (!childId || !selectedGuardianId) return;
    if (!selectedGuardian?.can_message) {
      setError("У родителя ещё нет активного аккаунта. Попросите администратора создать или восстановить доступ.");
      return;
    }
    try { const thread = await teacherApi.v2Direct(childId, selectedGuardianId); await loadThreads(); setThreadId(thread.id); setError(""); }
    catch (reason) { setError(userMessage(reason, "У родителя ещё нет активного аккаунта. Попросите администратора создать или восстановить доступ.")); }
  }
  function threadLabel(thread: ThreadV2) {
    if (thread.thread_type === "group") {
      return `${communicationAudienceLabels[thread.audience]} · ${thread.group_name}`;
    }
    if (thread.child_name && thread.guardian_id) {
      const guardian = guardians.find((item) => item.id === thread.guardian_id);
      const guardianName = guardian ? `${guardian.last_name} ${guardian.first_name}`.trim() : "родитель";
      return `${thread.child_name} · ${guardianName}`;
    }
    return "Личный диалог";
  }
  async function send(event: FormEvent) {
    event.preventDefault(); if (!threadId || !body.trim() || busy) return;
    setBusy(true);
    try { await teacherApi.v2SendMessage(threadId, body, clientMessageId.current); clientMessageId.current = crypto.randomUUID(); setBody(""); setMessages(await teacherApi.v2Messages(threadId)); await loadThreads(); setError(""); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <TeacherPageFrame title="Сообщения" eyebrow="Родители и группы">
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    <div className={styles.communicationLayout}><section className={styles.card}><h2>Новый диалог</h2><div className={styles.toolbar}>
      <GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} />
      <label>Аудитория<select value={groupAudience} onChange={(event) => setGroupAudience(event.target.value as typeof groupAudience)}><option value="all">Вся группа</option><option value="teachers">Воспитатели</option></select></label>
      <button className={styles.buttonSecondary} onClick={() => void openGroupThread()}>Чат группы</button>
      <label>Ребёнок<select value={childId} onChange={(event) => { setChildId(event.target.value); setGuardianId(""); }}>{children.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label>
      <label>Родитель<select value={selectedGuardianId} onChange={(event) => setGuardianId(event.target.value)}>{guardians.filter((item) => item.child_id === childId).map((guardian) => <option key={guardian.id} value={guardian.id}>{guardian.last_name} {guardian.first_name} · {relationLabels[guardian.relation_type]}{guardian.can_message ? "" : " · нет аккаунта"}</option>)}</select></label>
      <button className={styles.buttonSecondary} disabled={!selectedGuardian?.can_message} onClick={() => void openDirect()}>Личный диалог</button>
    </div></section>
      <section className={styles.card}><h2>Диалоги</h2><nav className={styles.communicationTabs} aria-label="Фильтр диалогов">{[["all","Все"],["direct","Личные"],["group","Группы"],["staff","Сотрудники"]].map(([key,label]) => <button key={key} type="button" aria-pressed={tab===key} className={tab===key?styles.button:styles.buttonSecondary} onClick={() => setTab(key as typeof tab)}>{label}</button>)}</nav>
        {threads.filter((thread) => tab === "all" || (tab === "direct" && thread.thread_type === "direct") || (tab === "group" && thread.thread_type === "group" && thread.audience === "all") || (tab === "staff" && thread.thread_type === "group" && thread.audience === "teachers")).length === 0 ? <p className={styles.muted}>Диалогов пока нет.</p> : <ul className={styles.list}>{threads.filter((thread) => tab === "all" || (tab === "direct" && thread.thread_type === "direct") || (tab === "group" && thread.thread_type === "group" && thread.audience === "all") || (tab === "staff" && thread.thread_type === "group" && thread.audience === "teachers")).map((thread) => <li key={thread.id}><button className={`${thread.id === threadId ? styles.button : styles.buttonSecondary} ${styles.conversationButton}`} onClick={() => setThreadId(thread.id)}>{threadLabel(thread)}{thread.unread_count > 0 && <span aria-label={`${thread.unread_count} непрочитанных`}> · {thread.unread_count}</span>}<small className={styles.threadPreview}>{thread.preview || "Нет сообщений"}</small></button></li>)}</ul>}</section>
      <section className={styles.card}><h2>{threads.find((item) => item.id === threadId) ? threadLabel(threads.find((item) => item.id === threadId)!) : "Сообщения"}</h2>{messages.length === 0 ? <p className={styles.muted}>Выберите диалог или начните новый.</p> : <ul className={styles.list}>{messages.map((message) => { const own = message.sender_user_id === current?.user.id; return <li className={`${styles.row} ${own ? styles.ownMessage : ""}`} key={message.id}><span className={styles.messageBubble}><strong>{own ? "Вы" : message.sender_name}</strong><span>{message.body}</span><small>{new Date(message.created_at).toLocaleString("ru-RU")}</small></span></li>; })}</ul>}<form className={styles.toolbar} onSubmit={(event) => void send(event)}><label>Новое сообщение<textarea value={body} maxLength={4000} onChange={(event) => { clientMessageId.current = crypto.randomUUID(); setBody(event.target.value); }} /></label><button className={styles.button} disabled={!threadId || !body.trim() || busy}>{busy ? "Отправка..." : "Отправить"}</button></form></section>
    </div>
  </TeacherPageFrame>;
}
