"use client";

/* eslint-disable @next/next/no-img-element */

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { parentStage6Api } from "@/lib/api/teacher";
import type { Announcement, ChildSummary, DiaryEntry, Message, PhotoAsset, Poll, Thread } from "@/types/teacher";
import styles from "@/features/teacher/cabinet.module.css";

type Tab = "announcements" | "messages" | "diary" | "polls" | "photos";

export function ParentStage6Cabinet() {
  return <AuthGate route="parent"><ParentContent /></AuthGate>;
}

function ParentContent() {
  const { current, clear } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("announcements");
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(() => Promise.all([
    parentStage6Api.children(), parentStage6Api.announcements(),
    parentStage6Api.threads(), parentStage6Api.polls(),
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

  return <main className={styles.stack} style={{ maxWidth: 1100, margin: "0 auto", padding: "1rem" }}>
    <header className={styles.card}><div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> Умный сад</div><h1>Кабинет родителя</h1><p>{current.organization.name} · {current.user.username}</p><button className={styles.buttonSecondary} onClick={() => void logout()}>Выйти</button></header>
    {error && <p className={styles.error}>{error}</p>}
    <nav className={styles.tabs}>{(["announcements", "messages", "diary", "polls", "photos"] as Tab[]).map((item) => <button className={tab === item ? styles.button : styles.buttonSecondary} key={item} onClick={() => setTab(item)}>{({ announcements: "Объявления", messages: "Сообщения", diary: "Дневник", polls: "Опросы", photos: "Фото" })[item]}</button>)}</nav>
    {tab === "announcements" && <Announcements items={announcements} />}
    {tab === "messages" && <Messages threads={threads} linkedChildren={children} reload={load} />}
    {tab === "diary" && <Diary linkedChildren={children} />}
    {tab === "polls" && <Polls items={polls} reload={load} />}
    {tab === "photos" && <Photos linkedChildren={children} />}
  </main>;
}

function Announcements({ items }: { items: Announcement[] }) {
  return <section className={styles.card}><h2>Объявления</h2><ul className={styles.list}>{items.map((item) => <li className={styles.row} key={item.id}><span><strong>{item.title}</strong><br/>{item.body}</span><small>{new Date(item.created_at).toLocaleDateString("ru-RU")}</small></li>)}</ul></section>;
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
      {threads.map((thread) => <button key={thread.id} className={thread.id === selectedThreadId ? styles.button : styles.buttonSecondary} onClick={() => setThreadId(thread.id)}>{thread.thread_type === "group" ? "Группа" : "Воспитатель"}</button>)}
    </section>
    <section className={styles.card}><h2>Сообщения</h2><ul className={styles.list}>{messages.map((message) => <li className={styles.row} key={message.id}>{message.body}</li>)}</ul><form className={styles.toolbar} onSubmit={(event) => void send(event)}><label>Ответ<textarea value={body} onChange={(event) => setBody(event.target.value)} /></label><button className={styles.button} disabled={!selectedThreadId}>Отправить</button></form></section>
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
