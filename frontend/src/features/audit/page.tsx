"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { auditApi } from "@/lib/api/audit";
import { userMessage } from "@/lib/api/client";
import type { JournalActor, JournalCategory, JournalItem } from "@/types/stage4";

const categories: [JournalCategory, string][] = [
  ["access", "Доступы и аккаунты"], ["people", "Люди и связи"], ["groups", "Группы и назначения"],
  ["operations", "Работа сада"], ["communications", "Связь"], ["documents", "Документы"],
  ["integrations", "Интеграции"], ["organization", "Настройки организации"],
];
const roleLabels = { DIRECTOR: "Директор", ADMIN: "Администратор", TEACHER: "Воспитатель", PARENT: "Родитель" };

export function AuditPage() {
  return <AuthGate route="director"><AppShell><JournalContent /></AppShell></AuthGate>;
}

function JournalContent() {
  const [category, setCategory] = useState<JournalCategory | "">("");
  const [actor, setActor] = useState("");
  const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<JournalItem[]>([]);
  const [actors, setActors] = useState<JournalActor[]>([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const limit = 25;
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const result = await auditApi.journal({ category: category || undefined, actor_user_id: actor || undefined,
        date_from: from || undefined, date_to: to || undefined, limit, offset });
      setItems(result.items); setActors(result.actors);
    } catch (reason) { setItems([]); setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [category, actor, from, to, offset]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  return <>
    <div className="page-heading"><span className="eyebrow">История</span><h1>Журнал действий</h1>
      <p>Действия в вашем детском саду. Имена показаны по текущим записям.</p></div>
    <div className="journal-filters">
      <label>Категория<select className="input" value={category} onChange={(event) => { setOffset(0); setCategory(event.target.value as JournalCategory | ""); }}>
        <option value="">Все</option>{categories.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label>
      <label>Участник<select className="input" value={actor} onChange={(event) => { setOffset(0); setActor(event.target.value); }}>
        <option value="">Все</option>{actors.map((item) => <option key={item.id} value={item.id}>{item.display_name} · {roleLabels[item.role]}</option>)}
      </select></label>
      <label>С даты<Input type="date" value={from} onChange={(event) => { setOffset(0); setFrom(event.target.value); }} /></label>
      <label>По дату<Input type="date" value={to} onChange={(event) => { setOffset(0); setTo(event.target.value); }} /></label>
      <Button variant="secondary" onClick={() => { setCategory(""); setActor(""); setFrom(""); setTo(""); setOffset(0); }}>Сбросить</Button>
    </div>
    {error && <Alert>{error}</Alert>}
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">События не найдены.</p> :
      <ol className="journal-list">{items.map((item) => <li className="card journal-card" key={item.id}>
        <div className="journal-meta"><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("ru-RU")}</time>
          <span>{categories.find(([key]) => key === item.category)?.[1]}</span></div>
        <h2>{item.summary}</h2>
        <p>{item.actor.display_name} · {roleLabels[item.actor.role]}</p>
        {item.safe_changes.length > 0 && <ul>{item.safe_changes.map((change) => <li key={change}>{change}</li>)}</ul>}
      </li>)}</ol>}
    <div className="audit-pagination"><Button variant="secondary" disabled={loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Назад</Button>
      <span>Записи {items.length ? offset + 1 : 0}–{offset + items.length}</span>
      <Button variant="secondary" disabled={loading || items.length < limit} onClick={() => setOffset(offset + limit)}>Далее</Button></div>
  </>;
}
