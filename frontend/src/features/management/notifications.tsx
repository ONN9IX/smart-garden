"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { ManagementControl, OperationalAlert } from "@/types/management";
import { ManagerPage, SectionError } from "./common";
import styles from "./director-redesign.module.css";

export function NotificationsPage() {
  return <ManagerPage><NotificationsContent /></ManagerPage>;
}

function NotificationsContent() {
  const [data, setData] = useState<ManagementControl | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [now, setNow] = useState(0);
  const request = useRef(0);
  const load = useCallback(async () => {
    const current = ++request.current;
    setLoading(true); setError(""); setData(null);
    try { const result = await managementApi.control(); if (current === request.current) { setData(result); setNow(Date.now()); } }
    catch (reason) { if (current === request.current) { setData(null); setError(userMessage(reason)); } }
    finally { if (current === request.current) setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); return () => { request.current += 1; }; }, [load]);

  async function changeAlert(alert: OperationalAlert, operation: "view" | "one_hour" | "next_morning") {
    setBusy(alert.alert_key); setError("");
    try {
      if (operation === "view") await managementApi.viewAlert(alert.alert_key);
      else await managementApi.snoozeAlert(alert.alert_key, operation);
      await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(""); }
  }
  async function readNotification(id: string) {
    setBusy(id); setError("");
    try { await managementApi.readNotification(id); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(""); }
  }

  const active = data?.alerts.filter((alert) => !alert.snoozed_until || new Date(alert.snoozed_until).getTime() <= now) ?? [];
  const snoozed = data?.alerts.filter((alert) => alert.snoozed_until && new Date(alert.snoozed_until).getTime() > now) ?? [];
  return <div className={styles.director}>
    <div className="page-heading"><span className="eyebrow">Работа сада</span><h1>Контроль</h1>
      <p>Актуальные условия сада и доставленные вам уведомления.</p></div>
    <SectionError error={error} retry={() => void load()} />
    {loading && !data ? <Loading /> : data && <>
      <div className="control-summary" aria-label="Сводка контроля">
        <div className="card"><span>Новые</span><strong>{data.summary.new}</strong></div>
        <div className="card"><span>Важные</span><strong>{data.summary.important}</strong></div>
        <div className="card"><span>Отложенные</span><strong>{data.summary.snoozed}</strong></div>
      </div>
      <section className="card section-card" aria-label="Требует внимания"><span className="eyebrow">Оперативные условия</span><h2>Требует внимания</h2>
        {active.length === 0 ? <p className="empty-state">Сейчас нет условий, требующих действия.</p> :
          <ul className="control-list">{active.map((alert) => <li key={alert.alert_key} className="control-item">
            <div><span className="eyebrow">{alert.priority === "important" ? "Важно" : "Информация"} · {alert.viewed_at ? "Просмотрено" : "Новое"}</span>
              <h3>{alert.title}</h3><p>{alert.context}</p></div>
            <div className="control-actions"><Link href={alert.action_href} onClick={() => void changeAlert(alert, "view")}>Открыть →</Link>
              {!alert.viewed_at && <Button variant="secondary" disabled={busy === alert.alert_key} onClick={() => void changeAlert(alert, "view")}>Просмотрено</Button>}
              <Button variant="secondary" disabled={busy === alert.alert_key} onClick={() => void changeAlert(alert, "one_hour")}>На 1 час</Button>
              <Button variant="secondary" disabled={busy === alert.alert_key} onClick={() => void changeAlert(alert, "next_morning")}>До утра</Button></div>
          </li>)}</ul>}
        {snoozed.length > 0 && <div><h3>Отложенные</h3><ul className="control-list">{snoozed.map((alert) =>
          <li key={alert.alert_key} className="control-item"><strong>{alert.title}</strong><span>До {new Date(alert.snoozed_until!).toLocaleString("ru-RU")}</span></li>
        )}</ul></div>}
      </section>
      <section className="card section-card" aria-label="Уведомления"><span className="eyebrow">Доставлено вам</span><h2>Уведомления</h2>
        {data.event_notifications.length === 0 ? <p className="empty-state">Уведомлений нет.</p> :
          <ul className="control-list">{data.event_notifications.map((item) => <li key={item.id} className="control-item">
            <div><strong>{item.title}</strong><p>{new Date(item.created_at).toLocaleString("ru-RU")} · {item.read_at ? "Прочитано" : "Новое"}</p></div>
            {!item.read_at && <Button variant="secondary" disabled={busy === item.id} onClick={() => void readNotification(item.id)}>Прочитано</Button>}
          </li>)}</ul>}
      </section>
    </>}
  </div>;
}
