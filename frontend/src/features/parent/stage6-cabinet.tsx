"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { parentStage6Api } from "@/lib/api/teacher";
import type { Announcement, ChildSummary, Message, Thread } from "@/types/teacher";
import styles from "@/features/teacher/cabinet.module.css";

type Tab = "announcements" | "messages";

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
  const [error, setError] = useState("");

  const load = useCallback(() => Promise.all([
    parentStage6Api.children(), parentStage6Api.announcements(), parentStage6Api.threads(),
  ]).then(([nextChildren, nextAnnouncements, nextThreads]) => {
    setChildren(nextChildren);
    setAnnouncements(nextAnnouncements);
    setThreads(nextThreads);
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
    <nav className={styles.tabs}>{(["announcements", "messages"] as Tab[]).map((item) => <button className={tab === item ? styles.button : styles.buttonSecondary} key={item} onClick={() => setTab(item)}>{({ announcements: "Объявления", messages: "Сообщения" })[item]}</button>)}</nav>
    {tab === "announcements" && <Announcements items={announcements} />}
    {tab === "messages" && <Messages threads={threads} linkedChildren={children} reload={load} />}
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
