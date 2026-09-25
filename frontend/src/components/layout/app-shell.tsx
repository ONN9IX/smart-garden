"use client";

/** Authenticated layout. Future modules remain disabled until their approved stages. */
import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { useAuth } from "@/features/auth/auth-provider";
import { ROLE_LABELS } from "@/types/auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

const futureSections = ["Родители", "Сотрудники", "Посещаемость", "Объявления", "Настройки"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { current, clear } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!current || current.user.role === "PARENT") return null;

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
          <Link href="/dashboard" className={`nav-item ${pathname === "/dashboard" ? "active" : ""}`} aria-current={pathname === "/dashboard" ? "page" : undefined}>Главная</Link>
          <Link href="/children" className={`nav-item ${pathname.startsWith("/children") ? "active" : ""}`} aria-current={pathname.startsWith("/children") ? "page" : undefined}>Дети</Link>
          <Link href="/groups" className={`nav-item ${pathname.startsWith("/groups") ? "active" : ""}`} aria-current={pathname.startsWith("/groups") ? "page" : undefined}>Группы</Link>
          {futureSections.map((section) => <span key={section} className="nav-item disabled" aria-disabled="true" title="Раздел будет реализован на следующем этапе">{section}</span>)}
        </nav>
        <p className="sidebar-note">Другие разделы появятся на следующих этапах.</p>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  </div>;
}
