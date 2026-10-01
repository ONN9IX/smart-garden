"use client";

/* eslint-disable @next/next/no-img-element */

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { featureEnabled, type ProductFeature } from "@/config/product-features";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { parentStage6Api } from "@/lib/api/teacher";
import type {
  Announcement, ChildSummary, DiaryEntry, Message, ParentToday, PhotoAsset, Poll, Thread,
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
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(() => Promise.all([
    parentStage6Api.children(),
    parentStage6Api.announcements(),
    parentStage6Api.threads(),
    featureEnabled("polls") ? parentStage6Api.polls() : Promise.resolve([] as Poll[]),
  ]).then(([nextChildren, nextAnnouncements, nextThreads, nextPolls]) => {
    setChildren(nextChildren);
    setAnnouncements(nextAnnouncements);
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
      <div className={styles.parentHeaderMain}><div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> Умный сад</div><h1>Кабинет родителя</h1><p className={styles.muted}>{current.organization.name} · {current.user.username}</p></div>
      <button className={styles.buttonSecondary} onClick={() => void logout()}>Выйти</button>
    </header>
    {error && <p className={styles.error}>{error}</p>}
    <nav className={styles.tabs} aria-label="Разделы кабинета">{tabs.filter(([, , feature]) => !feature || featureEnabled(feature)).map(([item, label]) => <button aria-pressed={tab === item} className={tab === item ? styles.button : styles.buttonSecondary} key={item} onClick={() => setTab(item)}>{label}</button>)}</nav>
    {tab === "today" && <Today linkedChildren={children} />}
    {tab === "announcements" && <Announcements items={announcements} />}
    {tab === "messages" && <Messages threads={threads} linkedChildren={children} reload={load} />}
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
    <h2>Сегодня</h2>
    <div className={styles.toolbar}>
      <label>Ребёнок<select value={selectedChildId} onChange={(event) => setChildId(event.target.value)}>{linkedChildren.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label>
    </div>
    {error && <p className={styles.error}>{error}</p>}
    {!data && !error && <p className={styles.muted}>Загружаем данные дня…</p>}
    {data && <div className={styles.stack}>
      <div className={styles.todaySummary}>
        <article className={`${styles.card} ${styles.todayIdentity}`}><strong>{data.child.last_name} {data.child.first_name}</strong><br/><small>Группа: {data.group.name}</small></article>
        <article className={styles.card}><span className={attendanceClass}>{attendanceLabel}</span><br/><small>{data.attendance.arrival_time ? `Приход: ${data.attendance.arrival_time.slice(0, 5)}` : "Отметку ставит воспитатель"}{data.attendance.departure_time ? ` · Уход: ${data.attendance.departure_time.slice(0, 5)}` : ""}</small></article>
      </div>
      <div><strong className={styles.scheduleTitle}>Расписание на сегодня</strong>{data.schedule.length === 0
        ? <p className={styles.muted}>На сегодня занятий в расписании нет.</p>
        : <ul className={styles.list}>{data.schedule.map((item) => <li className={styles.row} key={item.id}><span><strong>{item.title}</strong></span><small>{item.start_time.slice(0, 5)}–{item.end_time.slice(0, 5)}</small></li>)}</ul>}</div>
    </div>}
  </section>;
}

function Announcements({ items }: { items: Announcement[] }) {
  return <section className={styles.card}><h2>Объявления</h2>{items.length === 0 ? <p className={styles.muted}>Новых объявлений нет.</p> : <ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><span><strong>{item.title}</strong><br/>{item.body}</span><small>{new Date(item.created_at).toLocaleDateString("ru-RU")}</small></li>)}</ul>}</section>;
}

function Messages({ threads, linkedChildren, reload }: {
  threads: Thread[]; linkedChildren: ChildSummary[]; reload: () => Promise<unknown>;
}) {
  const [threadId, setThreadId] = useState(threads[0]?.id || "");
  const [childId, setChildId] = useState(linkedChildren[0]?.id || "");
  const [messages, setMessages] = useState<Message[]>([]);
  const [body, setBody] = useState("");
  const selectedThreadId = threadId || threads[0]?.id || "";
  const selectedChildId = childId || linkedChildren[0]?.id || "";

  useEffect(() => {
    if (selectedThreadId) parentStage6Api.messages(selectedThreadId).then(setMessages);
  }, [selectedThreadId]);
  const visibleMessages = selectedThreadId ? messages : [];

  async function openDirect() {
    if (!selectedChildId) return;
    const next = await parentStage6Api.direct(selectedChildId);
    setThreadId(next.id);
    await reload();
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!selectedThreadId || !body.trim()) return;
    await parentStage6Api.sendMessage(selectedThreadId, body);
    setBody("");
    setMessages(await parentStage6Api.messages(selectedThreadId));
  }

  return <div className={styles.grid}>
    <section className={styles.card}><h2>Диалоги</h2>
      <div className={styles.toolbar}>
        <label>Ребёнок<select value={selectedChildId} onChange={(event) => setChildId(event.target.value)}>{linkedChildren.map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select></label>
        <button className={styles.buttonSecondary} disabled={!selectedChildId} onClick={() => void openDirect()}>Открыть личный диалог</button>
      </div>
      {threads.length === 0 && <p className={styles.muted}>Диалогов пока нет.</p>}
      {threads.map((thread) => {
        const child = linkedChildren.find((item) => item.id === thread.child_id);
        const label = thread.thread_type === "group" ? "Чат группы" : child ? `Воспитатель · ${child.last_name} ${child.first_name}` : "Воспитатель";
        return <button key={thread.id} className={`${thread.id === selectedThreadId ? styles.button : styles.buttonSecondary} ${styles.conversationButton}`} onClick={() => setThreadId(thread.id)}>{label}</button>;
      })}
    </section>
    <section className={styles.card}><h2>Сообщения</h2>{visibleMessages.length === 0 ? <p className={styles.muted}>Выберите диалог или откройте новый.</p> : <ul className={styles.list}>{visibleMessages.map((message) => <li className={styles.row} key={message.id}><span className={styles.messageBubble}><span>{message.body}</span></span></li>)}</ul>}<form className={styles.toolbar} onSubmit={(event) => void send(event)}><label>Ответ<textarea value={body} onChange={(event) => setBody(event.target.value)} /></label><button className={styles.button} disabled={!selectedThreadId || !body.trim()}>Отправить</button></form></section>
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
