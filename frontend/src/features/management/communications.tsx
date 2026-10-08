"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { groupsApi } from "@/lib/api/groups";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { Group } from "@/types/stage2";
import type { ManagementMessage } from "@/types/management";
import { ManagerPage, SectionError, useQueryParam } from "./common";

export function CommunicationsPage() {
  return <ManagerPage><CommunicationsContent /></ManagerPage>;
}

function CommunicationsContent() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [items, setItems] = useState<ManagementMessage[]>([]);
  const [threadId, setThreadId] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<"all" | "teachers">("all");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const clientMessageId = useRef(crypto.randomUUID());

  useQueryParam("group_id", setGroupId);

  useEffect(() => {
    void groupsApi.list("active")
      .then((result) => setGroups(result.items))
      .catch((reason) => setError(userMessage(reason)));
  }, []);

  const load = useCallback(async () => {
    if (!groupId) { setItems([]); return; }
    setLoading(true); setError("");
    try {
      const thread = await managementApi.v2GroupThread(groupId, audience);
      setThreadId(thread.id);
      const messages = await managementApi.v2Messages(thread.id);
      setItems(messages);
      const last = messages.at(-1);
      if (last) await managementApi.v2MarkRead(thread.id, last.id);
    }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [audience, groupId]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!groupId || !body.trim()) return;
    setBusy(true); setError("");
    try {
      if (!threadId) return;
      await managementApi.v2SendMessage(threadId, body.trim(), clientMessageId.current);
      clientMessageId.current = crypto.randomUUID();
      setBody("");
      await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Общение</span><h1>Сообщения группы</h1><p>Управление доступно только в групповых каналах.</p></div>
    <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Выберите группу</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
    <label>Аудитория <select className="input" value={audience} onChange={(event) => setAudience(event.target.value as typeof audience)}><option value="all">Все участники</option><option value="teachers">Сотрудники</option></select></label>
    <SectionError error={error} retry={() => void load()} />
    {loading ? <Loading /> : groupId && items.length === 0 ? <p className="empty-state">Сообщений пока нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="card section-card"><strong>{item.sender_name}</strong><p>{item.body}</p><span className="muted">{new Date(item.created_at).toLocaleString("ru-RU")}</span></div></li>)}</ul>}
    {groupId && <form className="card section-card section-space" onSubmit={(event) => void send(event)}>
      <label>Сообщение<textarea className="input" rows={4} maxLength={4000} value={body} onChange={(event) => { clientMessageId.current = crypto.randomUUID(); setBody(event.target.value); }} /></label>
      <Button disabled={busy || !body.trim()}>{busy ? "Отправка..." : "Отправить"}</Button>
    </form>}
  </>;
}
