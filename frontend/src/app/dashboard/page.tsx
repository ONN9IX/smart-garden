"use client";

/** Technical dashboard displays only server-confirmed organization and role. */
import { AppShell } from "@/components/layout/app-shell";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { ROLE_LABELS } from "@/types/auth";

export default function DashboardPage() {
  return <AuthGate route="dashboard"><DashboardContent /></AuthGate>;
}

function DashboardContent() {
  const { current } = useAuth();
  if (!current) return null;
  return <AppShell><div className="page-heading"><span className="eyebrow">Главная</span><h1>Добро пожаловать</h1><p>Вы вошли в рабочий кабинет своего детского сада.</p></div>
    <section className="card context-card" aria-labelledby="context-heading"><h2 id="context-heading">Текущий доступ</h2>
      <dl className="context-list"><div><dt>Детский сад</dt><dd>{current.organization.name}</dd></div><div><dt>Пользователь</dt><dd>{current.user.username}</dd></div><div><dt>Роль</dt><dd>{ROLE_LABELS[current.user.role] ?? "Пользователь"}</dd></div></dl>
    </section>
  </AppShell>;
}
