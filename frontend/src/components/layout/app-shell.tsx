"use client";

/** Authenticated layout. Future modules remain disabled until their approved stages. */
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { useAuth } from "@/features/auth/auth-provider";
import { ROLE_LABELS } from "@/types/auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

const futureSections = ["Дети", "Группы", "Родители", "Сотрудники", "Посещаемость", "Объявления", "Настройки"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { current, clear } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!current) return null;

  async function logout() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await authApi.logout();
      clear();
      router.replace("/login");
    } catch (reason) {
      setError(userMessage(reason, "Не удалось выйти. Попробуйте ещё раз."));
      setBusy(false);
    }
  }

  return <div className="app-shell">
    <header className="app-header">
      <Link href="/dashboard" className="brand" aria-label="Умный сад — главная"><span className="brand-mark" aria-hidden="true">✳</span> Умный сад</Link>
      <div className="header-actions">
        <span className="organization-name">{current.organization.name}</span>
        <div className="header-user"><strong>{current.user.username}</strong><span>{ROLE_LABELS[current.user.role] ?? "Пользователь"}</span></div>
        <Button variant="secondary" onClick={() => void logout()} disabled={busy}>{busy ? "Выход..." : "Выйти"}</Button>
      </div>
    </header>
    {error && <div className="shell-alert"><Alert>{error}</Alert></div>}
    <div className="app-body">
      <aside className="sidebar" aria-label="Основное меню">
        <nav>
          <Link href="/dashboard" className="nav-item active" aria-current="page">Главная</Link>
          {futureSections.map((section) => <span key={section} className="nav-item disabled" aria-disabled="true" title="Раздел будет реализован на следующем этапе">{section}</span>)}
        </nav>
        <p className="sidebar-note">Другие разделы появятся на следующих этапах.</p>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  </div>;
}
