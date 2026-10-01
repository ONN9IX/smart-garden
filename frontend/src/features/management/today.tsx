"use client";

import { useCallback, useEffect, useState } from "react";
import { featureEnabled } from "@/config/product-features";
import { Alert } from "@/components/ui/alert";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { ManagementToday } from "@/types/management";

function label(kind: string) {
  const labels: Record<string, string> = {
    attendance_missing: "Не заполнена посещаемость",
    tasks_overdue: "Просроченные задачи",
    incidents_open: "Открытые происшествия",
    notifications_unread: "Непрочитанные уведомления",
    group_without_teacher: "Группа без активного воспитателя",
  };
  return labels[kind] ?? "Операционное внимание";
}

export function ManagementTodayPanel() {
  const [today, setToday] = useState<ManagementToday | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setError("");
    try { setToday(await managementApi.today()); }
    catch (reason) { setError(userMessage(reason, "Дополнительная сводка временно недоступна.")); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  const attentionItems = today?.attention_items.filter(
    (item) => item.kind !== "incidents_open" || featureEnabled("incidents"),
  ) ?? [];

  return <section className="section-space" aria-labelledby="stage6-today-heading">
    <div className="section-heading"><div><h2 id="stage6-today-heading">Требует внимания</h2><p className="muted">Операционная сводка по включённым модулям.</p></div></div>
    {error && <Alert>{error}</Alert>}
    {today && <>
      <div className="dashboard-grid">
        <article className="card metric-card"><span>Без воспитателя</span><strong>{today.groups_without_active_teacher_assignment}</strong></article>
        <article className="card metric-card"><span>Открытые задачи</span><strong>{today.open_tasks}</strong></article>
        <article className="card metric-card"><span>Просрочено</span><strong>{today.overdue_tasks}</strong></article>
        {featureEnabled("incidents") && <article className="card metric-card"><span>Происшествия</span><strong>{today.open_incidents}</strong></article>}
        <article className="card metric-card"><span>Новые уведомления</span><strong>{today.unread_notifications}</strong></article>
      </div>
      {attentionItems.length === 0
        ? <p className="empty-state">Критичных операционных сигналов нет.</p>
        : <ul className="record-list">{attentionItems.map((item, index) => <li key={item.kind + ":" + (item.entity_id ?? String(index))}>
          <div className="record-link"><strong>{label(item.kind)}</strong><span className="muted">{item.count != null ? "Количество: " + item.count : "Требуется проверка"}</span></div>
        </li>)}</ul>}
    </>}
  </section>;
}
