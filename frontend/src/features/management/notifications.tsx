"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { ManagementNotification } from "@/types/management";
import { notificationKindLabels } from "@/lib/presentation";
import { ManagerPage, SectionError } from "./common";

export function NotificationsPage() {
  return <ManagerPage><NotificationsContent /></ManagerPage>;
}

function NotificationsContent() {
  const [status, setStatus] = useState("unread");
  const [items, setItems] = useState<ManagementNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setItems((await managementApi.notifications(status)).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [status]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  return <>
    <div className="page-heading"><span className="eyebrow">Личное</span><h1>Уведомления</h1><p>Только ваши операционные уведомления.</p></div>
    <label>Показать <select className="input compact-input" value={status} onChange={(event) => setStatus(event.target.value)}><option value="unread">Непрочитанные</option><option value="read">Прочитанные</option><option value="all">Все</option></select></label>
    <SectionError error={error} retry={() => void load()} />
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">Уведомлений нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="record-link">
      <strong>{notificationKindLabels[item.kind] ?? "Новое уведомление"}</strong>
      <span className="muted">{item.entity_type} · {new Date(item.created_at).toLocaleString("ru-RU")} · {item.read_at ? "прочитано" : "новое"}</span>
      {!item.read_at && <Button variant="secondary" onClick={() => void managementApi.readNotification(item.id).then(load).catch((reason) => setError(userMessage(reason)))}>Прочитано</Button>}
    </div></li>)}</ul>}
  </>;
}
