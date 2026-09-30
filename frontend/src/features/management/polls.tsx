"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { groupsApi } from "@/lib/api/groups";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { Group } from "@/types/stage2";
import type { ManagementPoll } from "@/types/management";
import { ManagerPage, useQueryParam } from "./common";

export function PollsPage() {
  return <ManagerPage><PollsContent /></ManagerPage>;
}

function PollsContent() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [status, setStatus] = useState("all");
  const [items, setItems] = useState<ManagementPoll[]>([]);
  const [question, setQuestion] = useState("");
  const [optionsText, setOptionsText] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useQueryParam("group_id", setGroupId);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [groupList, polls] = await Promise.all([
        groupsApi.list("active"),
        managementApi.polls(groupId || undefined, status),
      ]);
      setGroups(groupList.items);
      setItems(polls.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [groupId, status]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    const options = optionsText.split("\n").map((value) => value.trim()).filter(Boolean);
    if (!groupId || options.length < 2) {
      setError("Укажите группу и минимум два варианта ответа.");
      return;
    }
    setBusy(true); setError(""); setMessage("");
    try {
      await managementApi.createPoll({ group_id: groupId, question: question.trim(), options });
      setQuestion(""); setOptionsText(""); setMessage("Опрос создан."); await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Обратная связь</span><h1>Опросы</h1><p>Результаты показываются агрегированно, без списка проголосовавших.</p></div>
    <div className="filter-row">
      <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Все группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">Все</option><option value="active">Активные</option><option value="closed">Закрытые</option></select></label>
    </div>
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    <form className="card section-card" onSubmit={(event) => void create(event)}>
      <h2>Новый опрос</h2>
      <label>Группа <select required className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Выберите</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Вопрос <Input required maxLength={500} value={question} onChange={(event) => setQuestion(event.target.value)} /></label>
      <label>Варианты — по одному в строке<textarea className="input" rows={4} value={optionsText} onChange={(event) => setOptionsText(event.target.value)} /></label>
      <Button disabled={busy}>{busy ? "Создание..." : "Создать опрос"}</Button>
    </form>
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">Опросов нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="card section-card">
      <h2>{item.question}</h2>
      <p className="muted">{item.status === "active" ? "Активен" : "Закрыт"} · Голосов: {item.total_votes}</p>
      <ul>{item.options.map((option) => <li key={option.id}>{option.label}: {option.vote_count}</li>)}</ul>
      {item.status === "active" && <Button variant="secondary" disabled={busy} onClick={() => void managementApi.closePoll(item.id).then(load).catch((reason) => setError(userMessage(reason)))}>Закрыть опрос</Button>}
    </div></li>)}</ul>}
  </>;
}
