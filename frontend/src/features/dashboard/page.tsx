"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { ManagementTodayPanel } from "@/features/management/today";
import { userMessage } from "@/lib/api/client";
import { dashboardApi } from "@/lib/api/dashboard";
import { ROLE_LABELS } from "@/types/auth";
import type { DashboardSummary } from "@/types/stage4";

function displayDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "long" }).format(new Date(year, month - 1, day));
}

const cards: Array<{ key: keyof DashboardSummary; label: string; href: string }> = [
  { key: "active_children", label: "Активные дети", href: "/children" },
  { key: "present", label: "Присутствуют", href: "/attendance" },
  { key: "absent", label: "Отсутствуют", href: "/attendance" },
  { key: "unknown", label: "Без отметки", href: "/attendance" },
  { key: "active_groups", label: "Активные группы", href: "/groups" },
  { key: "active_employees", label: "Активные сотрудники", href: "/employees" },
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
        {cards.map(({ key, label, href }) => <Link className="card metric-card metric-link" href={href} key={key}>
          <span>{label}</span><strong>{String(summary[key])}</strong><small>Открыть раздел →</small>
        </Link>)}
      </section>
      <section className="section-space" aria-labelledby="groups-dashboard-heading"><div className="section-heading">
        <div><h2 id="groups-dashboard-heading">Группы сегодня</h2><p className="muted">Учитываются текущие активные дети и их текущие группы.</p></div>
      </div>
        {summary.groups.length === 0 ? <p className="empty-state">Активных групп пока нет.</p>
          : <ul className="dashboard-groups">{summary.groups.map((group) => <li className="card group-summary" key={group.id}>
            <h3>{group.name}</h3><dl><div><dt>Дети</dt><dd>{group.active_children}</dd></div><div><dt>Присутствуют</dt><dd>{group.present}</dd></div><div><dt>Отсутствуют</dt><dd>{group.absent}</dd></div><div><dt>Без отметки</dt><dd>{group.unknown}</dd></div></dl>
          </li>)}</ul>}
      </section>
      <ManagementTodayPanel />
      <section className="card context-card section-space" aria-labelledby="context-heading"><h2 id="context-heading">Текущий доступ</h2>
        <dl className="context-list"><div><dt>Детский сад</dt><dd>{current.organization.name}</dd></div><div><dt>Пользователь</dt><dd>{current.user.username}</dd></div><div><dt>Роль</dt><dd>{ROLE_LABELS[current.user.role] ?? "Пользователь"}</dd></div></dl>
      </section>
    </>}
  </AppShell>;
}
