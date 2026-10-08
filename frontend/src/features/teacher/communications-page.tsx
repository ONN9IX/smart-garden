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
  const [messagesThreadId, setMessagesThreadId] = useState("");
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [guardians, setGuardians] = useState<GuardianContext[]>([]);
  const [childId, setChildId] = useState("");
  const [guardianId, setGuardianId] = useState("");
  const [body, setBody] = useState("");
  const [groupAudience, setGroupAudience] = useState<"all" | "teachers">("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const clientMessageId = useRef(crypto.randomUUID());
  const messageRequestId = useRef(0);
  const sending = useRef(false);
  const selectedThreadRef = useRef(threadId);
  const listRequestId = useRef(0);
  const groupIdRef = useRef(groupId);
  const childIdRef = useRef(childId);
  const guardianIdRef = useRef(guardianId);
  const [tab, setTab] = useState<"all" | "direct" | "group" | "staff">("all");
  const loadThreads = useCallback(() => {
    const request = ++listRequestId.current;
    return teacherApi.v2Threads().then((items) => {
      if (request !== listRequestId.current) return;
      setThreads(items);
      setThreadId((selected) => { const next = selected || items[0]?.id || ""; selectedThreadRef.current = next; return next; }); setError("");
    }).catch((reason) => { if (request === listRequestId.current) setError(userMessage(reason)); });
  }, []);
  useEffect(() => { void loadThreads(); }, [loadThreads]);
  useEffect(() => {
    const request = ++messageRequestId.current;
    if (!threadId) return () => { messageRequestId.current += 1; };
    teacherApi.v2Messages(threadId).then(async (items) => {
      if (messageRequestId.current !== request) return;
      setMessages(items); setMessagesThreadId(threadId);
      const last = items.at(-1);
      if (last) {
        try { await teacherApi.v2MarkRead(threadId, last.id); }
        catch (reason) {
          if (messageRequestId.current === request) { setMessages([]); setMessagesThreadId(""); setThreads((current) => current.filter((item) => item.id !== threadId)); selectedThreadRef.current = ""; setThreadId(""); setError(userMessage(reason)); }
          return;
        }
        if (messageRequestId.current === request) await loadThreads();
      }
    }).catch((reason) => {
      if (messageRequestId.current === request) { setMessages([]); setMessagesThreadId(""); setThreads((current) => current.filter((item) => item.id !== threadId)); selectedThreadRef.current = ""; setThreadId(""); setError(userMessage(reason)); }
    });
    return () => { messageRequestId.current += 1; };
  }, [threadId, loadThreads]);
  const groupContextRequest = useRef(0);
  useEffect(() => {
    const request = ++groupContextRequest.current;
    groupIdRef.current = groupId;
    if (!groupId) return () => { groupContextRequest.current += 1; };
    Promise.all([teacherApi.children(groupId), teacherApi.guardians(groupId)]).then(([nextChildren, nextGuardians]) => {
      if (groupContextRequest.current !== request) return;
      const firstChildId = nextChildren[0]?.id || "";
      childIdRef.current = firstChildId; guardianIdRef.current = "";
      setChildren(nextChildren); setGuardians(nextGuardians); setChildId(firstChildId); setError("");
    }).catch((reason) => { if (groupContextRequest.current === request) setError(userMessage(reason)); });
    return () => { groupContextRequest.current += 1; };
  }, [groupId]);
  const selectedGuardianId = guardianId || guardians.find((item) => item.child_id === childId)?.id || "";
  const selectedGuardian = guardians.find((item) => item.id === selectedGuardianId);
  function selectGroup(id: string) {
    groupIdRef.current = id;
    setChildren([]); setGuardians([]); setChildId(""); setGuardianId(""); setGroupId(id);
  }
  function selectChild(id: string) { childIdRef.current = id; guardianIdRef.current = ""; setChildId(id); setGuardianId(""); }
  function selectGuardian(id: string) { guardianIdRef.current = id; setGuardianId(id); }
  function selectThread(id: string) {
    selectedThreadRef.current = id;
    setMessages([]); setMessagesThreadId(""); setBody(""); clientMessageId.current = crypto.randomUUID(); setError(""); setThreadId(id);
  }
  async function openGroupThread() {
    if (!groupId) return;
    const groupAtStart = groupId;
    try { const thread = await teacherApi.v2GroupThread(groupAtStart, groupAudience); if (groupIdRef.current !== groupAtStart) return; await loadThreads(); selectThread(thread.id); }
    catch (reason) { if (groupIdRef.current === groupAtStart) setError(userMessage(reason)); }
  }
  async function openDirect() {
    if (!childId || !selectedGuardianId) return;
    if (!selectedGuardian?.can_message) {
      setError("У родителя ещё нет активного аккаунта. Попросите администратора создать или восстановить доступ.");
      return;
    }
    const childAtStart = childId; const guardianAtStart = selectedGuardianId;
    try { const thread = await teacherApi.v2Direct(childAtStart, guardianAtStart); if (childIdRef.current !== childAtStart || (guardianIdRef.current && guardianIdRef.current !== guardianAtStart)) return; await loadThreads(); selectThread(thread.id); }
    catch (reason) { if (childIdRef.current === childAtStart && (!guardianIdRef.current || guardianIdRef.current === guardianAtStart)) setError(userMessage(reason, "У родителя ещё нет активного аккаунта. Попросите администратора создать или восстановить доступ.")); }
  }
  function threadLabel(thread: ThreadV2) {
    if (thread.thread_type === "group") {
      return `${communicationAudienceLabels[thread.audience]} · ${thread.group_name}`;
    }
    if (thread.child_name && thread.guardian_id) {
      const guardian = guardians.find((item) => item.id === thread.guardian_id);
      const guardianName = guardian ? `${guardian.last_name} ${guardian.first_name}`.trim() : "родитель";
      const relation = guardian ? ` · ${relationLabels[guardian.relation_type]}` : "";
      return `${guardianName}${relation} · ${thread.child_name}`;
    }
    return "Личный диалог";
  }
  async function send(event: FormEvent) {
    event.preventDefault(); if (!threadId || !body.trim() || busy || sending.current || selectedThreadRef.current !== threadId) return;
    sending.current = true;
    setBusy(true);
    const threadAtStart = threadId;
    try {
      await teacherApi.v2SendMessage(threadAtStart, body, clientMessageId.current);
      if (selectedThreadRef.current !== threadAtStart) return;
      clientMessageId.current = crypto.randomUUID(); setBody("");
      const items = await teacherApi.v2Messages(threadAtStart);
      if (selectedThreadRef.current === threadAtStart) { setMessages(items); setMessagesThreadId(threadAtStart); }
      await loadThreads(); setError("");
    }
    catch (reason) { if (selectedThreadRef.current === threadAtStart) setError(userMessage(reason)); }
    finally { sending.current = false; setBusy(false); }
  }
  return <TeacherPageFrame title="Сообщения" eyebrow="Родители и группы">
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    <div className={styles.communicationLayout}><section className={styles.card}><h2>Новый диалог</h2><div className={styles.toolbar}>
      <GroupPicker groups={groups} groupId={groupId} setGroupId={selectGroup} />
      <label>Аудитория<select value={groupAudience} onChange={(event) => setGroupAudience(event.target.value as typeof groupAudience)}><option value="all">Вся группа</option><option value="teachers">Воспитатели</option></select></label>
      <button className={styles.buttonSecondary} onClick={() => void openGroupThread()}>Чат группы</button>
      <label>Ребёнок<select value={childId} onChange={(event) => selectChild(event.target.value)}>{children.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label>
      <label>Родитель<select value={selectedGuardianId} onChange={(event) => selectGuardian(event.target.value)}>{guardians.filter((item) => item.child_id === childId).map((guardian) => <option key={guardian.id} value={guardian.id}>{guardian.last_name} {guardian.first_name} · {relationLabels[guardian.relation_type]}{guardian.can_message ? "" : " · нет аккаунта"}</option>)}</select></label>
      <button className={styles.buttonSecondary} disabled={!selectedGuardian?.can_message} onClick={() => void openDirect()}>Личный диалог</button>
    </div></section>
      <section className={styles.card}><h2>Диалоги</h2><nav className={styles.communicationTabs} aria-label="Фильтр диалогов">{[["all","Все"],["direct","Личные"],["group","Группы"],["staff","Сотрудники"]].map(([key,label]) => <button key={key} type="button" aria-pressed={tab===key} className={tab===key?styles.button:styles.buttonSecondary} onClick={() => setTab(key as typeof tab)}>{label}</button>)}</nav>
        {threads.filter((thread) => tab === "all" || (tab === "direct" && thread.thread_type === "direct") || (tab === "group" && thread.thread_type === "group" && thread.audience === "all") || (tab === "staff" && thread.thread_type === "group" && thread.audience === "teachers")).length === 0 ? <p className={styles.muted}>Диалогов пока нет.</p> : <ul className={styles.list}>{threads.filter((thread) => tab === "all" || (tab === "direct" && thread.thread_type === "direct") || (tab === "group" && thread.thread_type === "group" && thread.audience === "all") || (tab === "staff" && thread.thread_type === "group" && thread.audience === "teachers")).map((thread) => <li key={thread.id}><button className={`${thread.id === threadId ? styles.button : styles.buttonSecondary} ${styles.conversationButton}`} onClick={() => selectThread(thread.id)}>{threadLabel(thread)}{thread.unread_count > 0 && <span aria-label={`${thread.unread_count} непрочитанных`}> · {thread.unread_count}</span>}<small className={styles.threadPreview}>{thread.preview || "Нет сообщений"}</small></button></li>)}</ul>}</section>
      <section className={styles.card}><h2>{threads.find((item) => item.id === threadId) ? threadLabel(threads.find((item) => item.id === threadId)!) : "Сообщения"}</h2>{messagesThreadId !== threadId || messages.length === 0 ? <p className={styles.muted}>Выберите диалог или начните новый.</p> : <ul className={styles.list}>{messages.map((message) => { const own = message.sender_user_id === current?.user.id; return <li className={`${styles.row} ${own ? styles.ownMessage : ""}`} key={message.id}><span className={styles.messageBubble}><strong>{own ? "Вы" : message.sender_name}</strong><span>{message.body}</span><small>{new Date(message.created_at).toLocaleString("ru-RU")}</small></span></li>; })}</ul>}<form className={styles.toolbar} onSubmit={(event) => void send(event)}><label>Новое сообщение<textarea value={body} maxLength={4000} onChange={(event) => { clientMessageId.current = crypto.randomUUID(); setBody(event.target.value); }} /></label><button className={styles.button} disabled={!threadId || !body.trim() || busy}>{busy ? "Отправка..." : "Отправить"}</button></form></section>
    </div>
  </TeacherPageFrame>;
}
