"use client";

/* eslint-disable @next/next/no-img-element */

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { featureEnabled, type ProductFeature } from "@/config/product-features";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { parentStage6Api } from "@/lib/api/teacher";
import type {
  AnnouncementV2, ChildSummary, DiaryEntry, EligibleTeacher, Message, ParentToday, PhotoAsset, Poll, ThreadV2,
} from "@/types/teacher";
import styles from "@/features/teacher/cabinet.module.css";

type Tab = "today" | "announcements" | "messages" | "diary" | "polls" | "photos";
type ParentTab = readonly [tab: Tab, label: string, feature?: ProductFeature];

export function ParentStage6Cabinet() {
  return <AuthGate route="parent"><ParentContent /></AuthGate>;
}

function ParentContent() {
  const { current, clear } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("today");
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [announcements, setAnnouncements] = useState<AnnouncementV2[]>([]);
  const [threads, setThreads] = useState<ThreadV2[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(() => Promise.all([
    parentStage6Api.children(),
    parentStage6Api.announcements(),
    parentStage6Api.v2Threads(),
    featureEnabled("polls") ? parentStage6Api.polls() : Promise.resolve([] as Poll[]),
  ]).then(([nextChildren, nextAnnouncements, nextThreads, nextPolls]) => {
    setChildren(nextChildren);
    // The list is navigation metadata only. Keep announcement text out of the
    // long-lived Parent list state; retrieve it from the authorized detail route on open.
    setAnnouncements(nextAnnouncements.map((item) => ({ ...item, body: "" })));
    setThreads(nextThreads);
    setPolls(nextPolls);
  }).catch((reason) => setError(userMessage(reason))), []);

  useEffect(() => { void load(); }, [load]);
  if (!current || current.user.role !== "PARENT") return null;

  async function logout() {
    try {
      await authApi.logout();
      clear();
      router.replace("/login");
    } catch (reason) {
      setError(userMessage(reason));
    }
  }

  const tabs: readonly ParentTab[] = [
    ["today", "Сегодня"],
    ["announcements", "Объявления"],
    ["messages", "Сообщения"],
    ["diary", "Дневник", "diary"],
    ["polls", "Опросы", "polls"],
    ["photos", "Фото", "photos"],
  ];

  return <main className={`${styles.stack} ${styles.parentShell}`}>
    <header className={`${styles.card} ${styles.parentHeader}`}>
      <div className={styles.parentHeaderMain}><div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> ПРОМАКС</div><h1>Кабинет родителя</h1><p className={styles.muted}>{current.organization.name} · {current.user.username}</p></div>
      <button className={styles.buttonSecondary} onClick={() => void logout()}>Выйти</button>
    </header>
    {error && <p className={styles.error}>{error}</p>}
    <nav className={styles.tabs} aria-label="Разделы кабинета">{tabs.filter(([, , feature]) => !feature || featureEnabled(feature)).map(([item, label]) => <button aria-pressed={tab === item} className={tab === item ? styles.button : styles.buttonSecondary} key={item} onClick={() => setTab(item)}>{label}</button>)}</nav>
    {tab === "today" && <Today linkedChildren={children} />}
    {tab === "announcements" && <Announcements items={announcements} />}
    {tab === "messages" && <Messages threads={threads} linkedChildren={children} reload={load} currentUserId={current.user.id} />}
    {featureEnabled("diary") && tab === "diary" && <Diary linkedChildren={children} />}
    {featureEnabled("polls") && tab === "polls" && <Polls items={polls} reload={load} />}
    {featureEnabled("photos") && tab === "photos" && <Photos linkedChildren={children} />}
  </main>;
}

function Today({ linkedChildren }: { linkedChildren: ChildSummary[] }) {
  const [childId, setChildId] = useState("");
  const [data, setData] = useState<ParentToday | null>(null);
  const [error, setError] = useState("");
  const selectedChildId = childId || linkedChildren[0]?.id || "";

  useEffect(() => {
    if (!selectedChildId) return;
    parentStage6Api.today(selectedChildId)
      .then((value) => { setData(value); setError(""); })
      .catch((reason) => { setData(null); setError(userMessage(reason)); });
  }, [selectedChildId]);

  if (linkedChildren.length === 0) {
    return <section className={styles.card}><h2>Сегодня</h2><p className={styles.muted}>Нет доступных карточек детей.</p></section>;
  }

  const attendanceLabel = data?.attendance.status === "present"
    ? "В детском саду"
    : data?.attendance.status === "absent"
      ? "Отсутствует"
      : "Пока не отмечен";

  const attendanceClass = data?.attendance.status === "present"
    ? `${styles.statusPill} ${styles.statusPresent}`
    : data?.attendance.status === "absent"
      ? `${styles.statusPill} ${styles.statusAbsent}`
      : `${styles.statusPill} ${styles.statusUnknown}`;

  return <section className={styles.card}>
    <h2>{data ? `Группа ${data.group.name}` : "Сегодня"}</h2>
    <div className={styles.toolbar}>
      <label>Ребёнок<select value={selectedChildId} onChange={(event) => setChildId(event.target.value)}>{linkedChildren.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label>
    </div>
    {error && <p className={styles.error}>{error}</p>}
    {!data && !error && <p className={styles.muted}>Загружаем данные дня…</p>}
    {data && <div className={styles.stack}>
      <div className={styles.todaySummary}>
        <article className={`${styles.card} ${styles.todayIdentity}`}><small>Ежедневная информация</small><br/><strong>{data.child.last_name} {data.child.first_name}</strong></article>
        <article className={styles.card}><span className={attendanceClass}>{attendanceLabel}</span><br/><small>{data.attendance.arrival_time ? `Приход: ${data.attendance.arrival_time.slice(0, 5)}` : "Отметку ставит воспитатель"}{data.attendance.departure_time ? ` · Уход: ${data.attendance.departure_time.slice(0, 5)}` : ""}</small></article>
      </div>
      <div><strong className={styles.scheduleTitle}>Расписание на сегодня</strong>{data.schedule.length === 0
        ? <p className={styles.muted}>На сегодня занятий в расписании нет.</p>
        : <ul className={styles.list}>{data.schedule.map((item) => <li className={styles.row} key={item.id}><span><strong>{item.title}</strong></span><small>{item.start_time.slice(0, 5)}–{item.end_time.slice(0, 5)}</small></li>)}</ul>}</div>
    </div>}
  </section>;
}

function Announcements({ items }: { items: AnnouncementV2[] }) {
  const [readIds, setReadIds] = useState<string[]>([]);
  const [openedId, setOpenedId] = useState("");
  const [openedItem, setOpenedItem] = useState<AnnouncementV2 | null>(null);
  const [loadingId, setLoadingId] = useState("");
  const [error, setError] = useState("");
  const requestVersion = useRef(0);
  useEffect(() => () => { requestVersion.current += 1; }, []);
  async function open(item: AnnouncementV2) {
    const request = ++requestVersion.current;
    if (openedId === item.id && openedItem?.id === item.id) {
      setOpenedId(""); setOpenedItem(null); setLoadingId(""); setError("");
      return;
    }
    setOpenedId(item.id);
    setOpenedItem(null);
    setLoadingId(item.id);
    setError("");
    try {
      const detail = await parentStage6Api.v2Announcement(item.id);
      if (requestVersion.current !== request || detail.id !== item.id) return;
      setOpenedItem(detail);
      if (item.unread && !readIds.includes(item.id)) {
        await parentStage6Api.readV2Announcement(item.id);
        if (requestVersion.current !== request) return;
        setReadIds((current) => current.includes(item.id) ? current : [...current, item.id]);
      }
    } catch {
      if (requestVersion.current === request) {
        setOpenedItem(null);
        setOpenedId("");
        setError("Объявление больше недоступно.");
      }
    } finally {
      if (requestVersion.current === request) setLoadingId("");
    }
  }
  return <section className={styles.card}><h2>Объявления</h2>{error && <p className={styles.error}>{error}</p>}{items.length === 0 ? <p className={styles.muted}>Новых объявлений нет.</p> : <ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><span><button type="button" className={styles.buttonSecondary} aria-expanded={openedId === item.id} onClick={() => void open(item)}><strong>{item.title}</strong></button><small className={styles.threadPreview}>{item.group_name || "Детский сад"} · {item.audience === "parents" ? "Родители" : item.audience === "staff" ? "Сотрудники" : "Все"}{item.unread && !readIds.includes(item.id) ? " · Новое" : ""}</small>{openedId === item.id && (loadingId === item.id ? <p className={styles.muted}>Проверяем доступ…</p> : openedItem?.id === item.id ? <p>{openedItem.body}</p> : null)}</span><small>{new Date(item.published_at).toLocaleDateString("ru-RU")}</small></li>)}</ul>}</section>;
}

function Messages({ threads, linkedChildren, reload, currentUserId }: {
  threads: ThreadV2[]; linkedChildren: ChildSummary[]; reload: () => Promise<unknown>; currentUserId: string;
}) {
  const [threadId, setThreadId] = useState(threads[0]?.id || "");
  const [childId, setChildId] = useState(linkedChildren[0]?.id || "");
  const [teachers, setTeachers] = useState<EligibleTeacher[]>([]);
  const [teacherId, setTeacherId] = useState("");
  const teacherIdRef = useRef(teacherId);
  const [tab, setTab] = useState<"all" | "direct" | "group">("all");
  const [messages, setMessages] = useState<Message[]>([]);
  const [messagesThreadId, setMessagesThreadId] = useState("");
  const [body, setBody] = useState("");
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [unavailableIds, setUnavailableIds] = useState<string[]>([]);
  const clientMessageId = useRef(crypto.randomUUID());
  const requestId = useRef(0);
  const groupRequestId = useRef(0);
  const sendingRef = useRef(false);
  const selectedChildId = childId || linkedChildren[0]?.id || "";
  const selectedChildRef = useRef(selectedChildId);

  useEffect(() => { selectedChildRef.current = selectedChildId; }, [selectedChildId]);
  useEffect(() => {
    let active = true;
    const context = ++groupRequestId.current;
    if (!selectedChildId) return () => { active = false; };
    parentStage6Api.today(selectedChildId).then((data) => {
      if (active && groupRequestId.current === context && selectedChildRef.current === selectedChildId) setGroupId(data.group.id);
    }).catch(() => { if (active && groupRequestId.current === context) setGroupId(""); });
    return () => { active = false; };
  }, [selectedChildId]);

  useEffect(() => {
    let active = true;
    if (selectedChildId) parentStage6Api.v2EligibleTeachers(selectedChildId).then((items) => {
      if (!active || selectedChildRef.current !== selectedChildId) return;
      setTeachers(items);
      const firstTeacherId = items[0]?.employee_id || "";
      teacherIdRef.current = firstTeacherId;
      setTeacherId(firstTeacherId);
    }).catch(() => { if (active && selectedChildRef.current === selectedChildId) setTeachers([]); });
    return () => { active = false; };
  }, [selectedChildId]);

  const childThreads = threads.filter((thread) => !unavailableIds.includes(thread.id) && (
    thread.thread_type === "direct" ? thread.child_id === selectedChildId :
      thread.thread_type === "group" && thread.audience === "all" && Boolean(groupId) && thread.group_id === groupId
  ));
  const visibleThreads = childThreads.filter((thread) => tab === "all" || (tab === "direct" && thread.thread_type === "direct") || (tab === "group" && thread.thread_type === "group"));
  const selectedThreadId = threadId ? (visibleThreads.some((thread) => thread.id === threadId) ? threadId : "") : visibleThreads[0]?.id || "";
  const activeThreadId = useRef(selectedThreadId);
  useEffect(() => {
    const request = ++requestId.current;
    if (!selectedThreadId) return () => { requestId.current += 1; };
    parentStage6Api.v2Messages(selectedThreadId).then(async (items) => {
      if (requestId.current !== request) return;
      setMessages(items);
      setMessagesThreadId(selectedThreadId);
      const last = items.at(-1);
      if (last) {
        try { await parentStage6Api.v2MarkRead(selectedThreadId, last.id); }
        catch (reason) {
          if (requestId.current === request) { setMessages([]); setMessagesThreadId(""); setUnavailableIds((current) => [...new Set([...current, selectedThreadId])]); setThreadId(""); activeThreadId.current = ""; setError(userMessage(reason)); }
          return;
        }
        if (requestId.current === request) await reload();
      }
    }).catch((reason) => {
      if (requestId.current === request) { setMessages([]); setMessagesThreadId(""); setUnavailableIds((current) => [...new Set([...current, selectedThreadId])]); setThreadId(""); setError(userMessage(reason)); }
    });
    return () => { requestId.current += 1; };
  }, [selectedThreadId, reload]);
  const visibleMessages = selectedThreadId && messagesThreadId === selectedThreadId && visibleThreads.some((thread) => thread.id === selectedThreadId) ? messages : [];

  function changeChild(nextChildId: string) {
    selectedChildRef.current = nextChildId;
    groupRequestId.current += 1;
    requestId.current += 1;
    setChildId(nextChildId);
    setGroupId("");
    setThreadId("");
    activeThreadId.current = "";
    setMessages([]);
    setMessagesThreadId("");
    setBody("");
    setError("");
    setTeachers([]);
    teacherIdRef.current = "";
    setTeacherId("");
    clientMessageId.current = crypto.randomUUID();
  }

  async function openDirect() {
    if (!selectedChildId || !teacherId) return;
    const childAtStart = selectedChildId;
    const teacherAtStart = teacherId;
    const next = await parentStage6Api.v2Direct(childAtStart, teacherAtStart);
    if (selectedChildRef.current !== childAtStart || teacherIdRef.current !== teacherAtStart || next.child_id !== childAtStart || next.teacher_employee_id !== teacherAtStart) return;
    activeThreadId.current = next.id;
    setThreadId(next.id);
    await reload();
  }

  async function openGroup() {
    if (!selectedChildId) return;
    const childAtStart = selectedChildId;
    const childContext = await parentStage6Api.today(childAtStart);
    if (selectedChildRef.current !== childAtStart) return;
    const next = await parentStage6Api.v2GroupThread(childContext.group.id);
    if (selectedChildRef.current !== childAtStart || next.group_id !== childContext.group.id || next.audience !== "all") return;
    activeThreadId.current = next.id;
    setThreadId(next.id);
    await reload();
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (sendingRef.current || !selectedThreadId || !body.trim() || !visibleThreads.some((thread) => thread.id === selectedThreadId) || (activeThreadId.current && activeThreadId.current !== selectedThreadId)) return;
    activeThreadId.current = selectedThreadId;
    sendingRef.current = true; setSending(true); setError("");
    const threadAtStart = selectedThreadId; const childAtStart = selectedChildId; const messageId = clientMessageId.current; const draft = body;
    try {
      await parentStage6Api.v2SendMessage(threadAtStart, draft, messageId);
      if (selectedChildRef.current !== childAtStart || activeThreadId.current !== threadAtStart) return;
      clientMessageId.current = crypto.randomUUID(); setBody(""); setMessages(await parentStage6Api.v2Messages(threadAtStart)); await reload();
    } catch (reason) {
      if (selectedChildRef.current === childAtStart) {
        setError(userMessage(reason));
        const message = userMessage(reason);
        if (/404|не найден|доступ/i.test(message)) { setMessages([]); setMessagesThreadId(""); setUnavailableIds((current) => [...new Set([...current, threadAtStart])]); setThreadId(""); activeThreadId.current = ""; }
      }
    } finally { sendingRef.current = false; setSending(false); }
  }

  function selectThread(id: string) { if (!visibleThreads.some((thread) => thread.id === id)) return; requestId.current += 1; setMessages([]); setMessagesThreadId(""); setBody(""); setError(""); clientMessageId.current = crypto.randomUUID(); activeThreadId.current = id; setThreadId(id); }
  function selectTab(nextTab: "all" | "direct" | "group") {
    const nextThreads = childThreads.filter((thread) => nextTab === "all" || (nextTab === "direct" && thread.thread_type === "direct") || (nextTab === "group" && thread.thread_type === "group"));
    activeThreadId.current = nextThreads.some((thread) => thread.id === threadId) ? threadId : threadId ? "" : nextThreads[0]?.id || "";
    setTab(nextTab);
  }
  function selectTeacher(id: string) { teacherIdRef.current = id; setTeacherId(id); }
  const selectedThread = visibleThreads.find((thread) => thread.id === selectedThreadId);
  return <div className={styles.communicationLayout}>
    <section className={styles.card}><h2>Новый диалог</h2>
      <div className={styles.toolbar}>
        <label>Ребёнок<select value={selectedChildId} onChange={(event) => changeChild(event.target.value)}>{linkedChildren.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label>
        <label>Воспитатель<select value={teacherId} onChange={(event) => selectTeacher(event.target.value)}>{teachers.map((teacher) => <option key={teacher.employee_id} value={teacher.employee_id}>{teacher.display_name}</option>)}</select></label>
        <button className={styles.buttonSecondary} disabled={!selectedChildId || !teacherId} onClick={() => void openDirect()}>Личный диалог</button>
        <button className={styles.buttonSecondary} disabled={!selectedChildId} onClick={() => void openGroup()}>Группа</button>
      </div>
    </section>
    <section className={styles.card}><h2>Диалоги</h2><nav className={styles.communicationTabs} aria-label="Фильтр диалогов">{[["all","Все"],["direct","Личные"],["group","Группа"]].map(([key,label]) => <button key={key} type="button" aria-pressed={tab===key} className={tab===key?styles.button:styles.buttonSecondary} onClick={() => selectTab(key as typeof tab)}>{label}</button>)}</nav>{visibleThreads.length === 0 ? <p className={styles.muted}>Диалогов пока нет.</p> : visibleThreads.map((thread) => <button key={thread.id} className={`${thread.id === selectedThreadId ? styles.button : styles.buttonSecondary} ${styles.conversationButton}`} onClick={() => selectThread(thread.id)}>{thread.thread_type === "group" ? `Группа · ${thread.group_name}` : `${thread.teacher_name || "Воспитатель"} · ${thread.child_name || "Ребёнок"}`}<small className={styles.threadPreview}>{thread.preview || "Нет сообщений"}{thread.unread_count ? ` · ${thread.unread_count} новых` : ""}</small></button>)}</section>
    <section className={styles.card}><h2>{selectedThread?.thread_type === "direct" ? `${selectedThread.teacher_name || "Воспитатель"} · ${selectedThread.child_name || "Ребёнок"}` : selectedThread?.thread_type === "group" ? `Группа · ${selectedThread.group_name}` : "Сообщения"}</h2>{error && <p className={styles.error}>{error}</p>}{visibleMessages.length === 0 ? <p className={styles.muted}>Выберите диалог или откройте новый.</p> : <ul className={styles.list}>{visibleMessages.map((message) => { const own = message.sender_user_id === currentUserId; return <li className={`${styles.row} ${own ? styles.ownMessage : ""}`} key={message.id}><span className={styles.messageBubble}><strong>{own ? "Вы" : message.sender_name}</strong><span>{message.body}</span></span></li>; })}</ul>}<form className={styles.toolbar} onSubmit={(event) => void send(event)}><label>Ответ<textarea value={body} onChange={(event) => { clientMessageId.current = crypto.randomUUID(); setBody(event.target.value); }} /></label><button className={styles.button} disabled={!selectedThreadId || !body.trim() || sending}>{sending ? "Отправка..." : "Отправить"}</button></form></section>
  </div>;
}

function Diary({ linkedChildren }: { linkedChildren: ChildSummary[] }) {
  const [childId, setChildId] = useState(linkedChildren[0]?.id || "");
  const [items, setItems] = useState<DiaryEntry[]>([]);
  const selectedChildId = childId || linkedChildren[0]?.id || "";

  useEffect(() => {
    if (selectedChildId) parentStage6Api.diary(selectedChildId).then(setItems);
  }, [selectedChildId]);

  return <section className={styles.card}><h2>Дневник ребёнка</h2><select value={selectedChildId} onChange={(event) => setChildId(event.target.value)}>{linkedChildren.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select><ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><span>{item.note}</span><small>{item.date}</small></li>)}</ul></section>;
}

function Polls({ items, reload }: { items: Poll[]; reload: () => Promise<unknown> }) {
  return <section className={styles.card}><h2>Опросы</h2><ul className={styles.list}>{items.map((poll) => <li key={poll.id}><strong>{poll.question}</strong><div className={styles.toolbar}>{poll.options.map((option) => <button key={option.id} disabled={poll.status !== "active" || Boolean(poll.selected_option_id)} className={poll.selected_option_id === option.id ? styles.button : styles.buttonSecondary} onClick={() => void parentStage6Api.vote(poll.id, option.id).then(reload)}>{option.label}</button>)}</div></li>)}</ul></section>;
}

function Photos({ linkedChildren }: { linkedChildren: ChildSummary[] }) {
  const [childId, setChildId] = useState(linkedChildren[0]?.id || "");
  const [items, setItems] = useState<PhotoAsset[]>([]);
  const selectedChildId = childId || linkedChildren[0]?.id || "";

  useEffect(() => {
    if (selectedChildId) parentStage6Api.photos(selectedChildId).then(setItems);
  }, [selectedChildId]);

  return <section className={styles.card}><h2>Фото</h2><select value={selectedChildId} onChange={(event) => setChildId(event.target.value)}>{linkedChildren.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select><div className={styles.grid}>{items.map((item) => <div key={item.id}><img className={styles.photo} src={parentStage6Api.photoContent(item.id)} alt="Фото группы" /></div>)}</div></section>;
}
