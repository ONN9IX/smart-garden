"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { ManagementAttentionItem, ManagementToday } from "@/types/management";

function displayDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "long" }).format(new Date(year, month - 1, day));
}

function attentionText(item: ManagementAttentionItem, today: ManagementToday) {
  const group = today.groups.find((candidate) => candidate.group_id === item.entity_id);
  switch (item.kind) {
    case "attendance_missing":
      return `${group?.group_name ?? "Группа"}: без отметки ${group?.unknown ?? item.count ?? 0}, уточнить приход ${group?.needs_arrival ?? 0}`;
    case "group_without_teacher":
      return `${group?.group_name ?? "Группа"}: нет активного воспитателя`;
    case "tasks_overdue":
      return `Просрочено задач: ${item.count ?? today.overdue_tasks}`;
    case "group_without_schedule":
      return `${group?.group_name ?? "Группа"}: нет недельного расписания`;
    case "notifications_unread":
      return `Непрочитанных уведомлений: ${item.count ?? today.unread_notifications}`;
    default:
      return null;
  }
}

function attentionHref(item: ManagementAttentionItem) {
  if (item.kind === "group_without_teacher" || item.kind === "group_without_schedule") {
    return item.entity_id ? `/groups/${item.entity_id}` : "/groups";
  }
  if (item.kind === "tasks_overdue") return "/tasks";
  if (item.kind === "notifications_unread") return "/notifications";
  return "/attendance";
}

const metricCards = [
  { key: "on_site", label: "В саду", href: "/attendance", tone: "mint" },
  { key: "departed", label: "Ушли", href: "/attendance", tone: "blue" },
  { key: "absent", label: "Отсутствуют", href: "/attendance", tone: "blue" },
  { key: "unknown", label: "Без отметки", href: "/attendance", tone: "amber" },
  { key: "needs_arrival", label: "Уточнить приход", href: "/attendance", tone: "orange" },
  { key: "active_groups", label: "Активные группы", href: "/groups", tone: "violet" },
  { key: "groups_without_active_teacher_assignment", label: "Без воспитателя", href: "/groups", tone: "rose" },
  { key: "overdue_tasks", label: "Просроченные задачи", href: "/tasks", tone: "orange" },
] as const;

export function ManagementTodayPanel() {
  const [today, setToday] = useState<ManagementToday | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try { setToday(await managementApi.today()); }
    catch (reason) { setError(userMessage(reason, "Не удалось загрузить данные за сегодня.")); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  if (loading) return <section className="today-loading"><Loading /></section>;
  if (error || !today) return <section className="today-error">
    <Alert>{error || "Данные за сегодня пока недоступны."}</Alert>
    <Button variant="secondary" onClick={() => void load()}>Повторить</Button>
  </section>;

  const attention = today.attention_items
    .map((item) => ({ item, text: attentionText(item, today) }))
    .filter((entry): entry is { item: ManagementAttentionItem; text: string } => Boolean(entry.text));

  return <div className="today-page">
    <header className="today-heading">
      <div><span className="eyebrow">Оперативная картина</span><h1>Сегодня</h1>
        <p><time dateTime={today.date}>{displayDate(today.date)}</time> · по времени детского сада</p>
      </div>
      <Link className="today-primary-action" href="/attendance">Открыть посещаемость <span aria-hidden="true">→</span></Link>
    </header>

    <section className="today-metrics" aria-label="Показатели за сегодня">
      {metricCards.map(({ key, label, href, tone }) => <Link key={key} href={href}
        className={`today-metric today-metric-${tone}`}>
        <span>{label}</span><strong>{today[key].toLocaleString("ru-RU")}</strong>
        <small>Открыть раздел <span aria-hidden="true">↗</span></small>
      </Link>)}
    </section>
    <p className="muted">Посещали сегодня: {today.present}</p>

    <div className="today-main-grid">
      <section className="today-groups" aria-labelledby="today-groups-heading">
        <div className="today-section-heading"><div><span className="eyebrow">Работа сада</span>
          <h2 id="today-groups-heading">Группы сегодня</h2></div>
          <Link href="/groups">Все группы <span aria-hidden="true">→</span></Link>
        </div>
        {today.groups.length === 0 ? <p className="empty-state">Активных групп пока нет.</p> :
          <ul className="today-group-list">{today.groups.map((group) => <li className="today-group-card" key={group.group_id}>
            <div className="today-group-title"><Link href={`/groups/${group.group_id}`}>{group.group_name}</Link>
              <span>{group.active_children} {group.active_children === 1 ? "ребёнок" : "детей"}</span></div>
            <dl className="today-group-counts">
              <div><dt>В саду</dt><dd>{group.on_site}</dd></div>
              <div><dt>Ушли</dt><dd>{group.departed}</dd></div>
              <div><dt>Отсутствуют</dt><dd>{group.absent}</dd></div>
              <div><dt>Без отметки</dt><dd>{group.unknown}</dd></div>
              {group.needs_arrival > 0 && <div><dt>Уточнить приход</dt><dd>{group.needs_arrival}</dd></div>}
            </dl>
            <div className="today-group-status">
              <span className={group.has_active_teacher ? "state-good" : "state-missing"}>
                {group.has_active_teacher ? "Воспитатель есть" : "Без воспитателя"}
              </span>
              <span className={group.has_active_weekly_schedule ? "state-good" : "state-missing"}>
                {group.has_active_weekly_schedule ? "Расписание есть" : "Без расписания"}
              </span>
            </div>
          </li>)}</ul>}
      </section>

      <aside className="today-attention" aria-labelledby="today-attention-heading">
        <div className="today-section-heading"><div><span className="eyebrow">Приоритеты</span>
          <h2 id="today-attention-heading">Требует внимания</h2></div><span className="attention-count">{attention.length}</span></div>
        {attention.length === 0 ? <p className="today-all-clear">Всё отмечено. Срочных действий нет.</p> :
          <ul className="today-attention-list">{attention.map(({ item, text }, index) => <li key={`${item.kind}:${item.entity_id ?? index}`}>
            <span className="attention-dot" aria-hidden="true" />
            <Link href={attentionHref(item)}>{text}<span aria-hidden="true"> →</span></Link>
          </li>)}</ul>}
      </aside>
    </div>

    <Link className="today-task-summary" href="/tasks">
      <span className="task-summary-icon" aria-hidden="true">✓</span>
      <span><strong>Задачи сада</strong><small>Открытые задачи и ход работы</small></span>
      <strong className="task-summary-count">{today.open_tasks}</strong>
      <span className="task-summary-link">Открыть задачи →</span>
    </Link>
  </div>;
}
