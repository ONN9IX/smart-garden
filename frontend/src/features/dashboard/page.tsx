"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { userMessage } from "@/lib/api/client";
import { dashboardApi } from "@/lib/api/dashboard";
import { ROLE_LABELS } from "@/types/auth";
import type { DashboardSummary } from "@/types/stage4";

function displayDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "long" }).format(new Date(year, month - 1, day));
}

const cards: Array<{ key: keyof DashboardSummary; label: string }> = [
  { key: "active_children", label: "Активные дети" },
  { key: "present", label: "Присутствуют" },
  { key: "absent", label: "Отсутствуют" },
  { key: "unknown", label: "Без отметки" },
  { key: "active_groups", label: "Активные группы" },
  { key: "active_employees", label: "Активные сотрудники" },
];

export function DashboardPage() {
  return <AuthGate route="dashboard"><DashboardContent /></AuthGate>;
}

function DashboardContent() {
  const { current } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setSummary(await dashboardApi.summary()); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  if (!current) return null;

  return <AppShell>
    <div className="page-heading"><span className="eyebrow">Главная</span><h1>Оперативная сводка</h1>
      <p>{summary ? `Данные на ${displayDate(summary.date)} по времени детского сада.` : "Текущая ситуация в детском саду."}</p></div>
    {error && <Alert>{error}</Alert>}
    {loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : summary && <>
      <section className="dashboard-grid" aria-label="Основные показатели">
        {cards.map(({ key, label }) => <article className="card metric-card" key={key}>
          <span>{label}</span><strong>{String(summary[key])}</strong>
        </article>)}
      </section>
      <section className="section-space" aria-labelledby="groups-dashboard-heading"><div className="section-heading">
        <div><h2 id="groups-dashboard-heading">Группы сегодня</h2><p className="muted">Учитываются текущие активные дети и их текущие группы.</p></div>
      </div>
        {summary.groups.length === 0 ? <p className="empty-state">Активных групп пока нет.</p>
          : <ul className="dashboard-groups">{summary.groups.map((group) => <li className="card group-summary" key={group.id}>
            <h3><Link className="text-link" href={`/groups/${group.id}`}>{group.name}</Link></h3><dl><div><dt>Дети</dt><dd>{group.active_children}</dd></div><div><dt>Присутствуют</dt><dd>{group.present}</dd></div><div><dt>Отсутствуют</dt><dd>{group.absent}</dd></div><div><dt>Без отметки</dt><dd>{group.unknown}</dd></div></dl>
          </li>)}</ul>}
      </section>
      <section className="section-space" aria-labelledby="quick-actions-heading">
        <div className="section-heading"><div><h2 id="quick-actions-heading">Быстрые действия</h2><p className="muted">Переходы к уже доступным разделам управления.</p></div></div>
        <ul className="record-list">
          {[
            ["/groups", "Группы"], ["/children", "Дети"], ["/guardians", "Родители"],
            ["/employees", "Сотрудники"], ["/attendance", "Посещаемость"], ["/announcements", "Объявления"],
            ...(current.user.role === "DIRECTOR" ? [["/audit", "Аудит"]] : []),
          ].map(([href, label]) => <li key={href}><Link className="record-link" href={href}><strong>{label}</strong><span className="muted">Открыть раздел</span></Link></li>)}
        </ul>
      </section>
      <section className="card context-card section-space" aria-labelledby="context-heading"><h2 id="context-heading">Текущий доступ</h2>
        <dl className="context-list"><div><dt>Детский сад</dt><dd>{current.organization.name}</dd></div><div><dt>Пользователь</dt><dd>{current.user.username}</dd></div><div><dt>Роль</dt><dd>{ROLE_LABELS[current.user.role] ?? "Пользователь"}</dd></div></dl>
      </section>
    </>}
  </AppShell>;
}
