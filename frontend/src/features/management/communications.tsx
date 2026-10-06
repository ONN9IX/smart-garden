"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { groupsApi } from "@/lib/api/groups";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { Group } from "@/types/stage2";
import type { ManagementMessage } from "@/types/management";
import { communicationAudienceLabels } from "@/lib/presentation";
import { ManagerPage, SectionError, useQueryParam } from "./common";

export function CommunicationsPage() {
  return <ManagerPage><CommunicationsContent /></ManagerPage>;
}

function CommunicationsContent() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [items, setItems] = useState<ManagementMessage[]>([]);
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<"all" | "parents" | "teachers">("all");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useQueryParam("group_id", setGroupId);

  useEffect(() => {
    void groupsApi.list("active")
      .then((result) => setGroups(result.items))
      .catch((reason) => setError(userMessage(reason)));
  }, []);

  const load = useCallback(async () => {
    if (!groupId) { setItems([]); return; }
    setLoading(true); setError("");
    try { setItems((await managementApi.groupMessages(groupId, audience)).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [audience, groupId]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!groupId || !body.trim()) return;
    setBusy(true); setError("");
    try {
      await managementApi.sendGroupMessage(groupId, body.trim(), audience);
      setBody("");
      await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Общение</span><h1>Сообщения группы</h1><p>Выберите аудиторию сообщения. Личные диалоги воспитатель ↔ родитель здесь недоступны.</p></div>
    <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Выберите группу</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
    <label>Аудитория <select className="input" value={audience} onChange={(event) => setAudience(event.target.value as typeof audience)}>{Object.entries(communicationAudienceLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <SectionError error={error} retry={() => void load()} />
    {loading ? <Loading /> : groupId && items.length === 0 ? <p className="empty-state">Сообщений пока нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="card section-card"><strong>{item.sender_name}</strong><p>{item.body}</p><span className="muted">{new Date(item.created_at).toLocaleString("ru-RU")}</span></div></li>)}</ul>}
    {groupId && <form className="card section-card section-space" onSubmit={(event) => void send(event)}>
      <label>Сообщение<textarea className="input" rows={4} maxLength={4000} value={body} onChange={(event) => setBody(event.target.value)} /></label>
      <Button disabled={busy || !body.trim()}>{busy ? "Отправка..." : "Отправить"}</Button>
    </form>}
  </>;
}
