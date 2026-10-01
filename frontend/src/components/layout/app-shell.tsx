"use client";

/** Authenticated layout with reversible product-module route gates. */
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { routeEnabled } from "@/config/product-features";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { useAuth } from "@/features/auth/auth-provider";
import { ROLE_LABELS } from "@/types/auth";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ManagementNav } from "@/components/layout/management-nav";
import { TeacherNav } from "@/components/layout/teacher-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { current, clear } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const disabledRoute = !routeEnabled(pathname);

  useEffect(() => {
    if (!current || current.user.role === "PARENT" || !disabledRoute) return;
    router.replace(current.user.role === "TEACHER" ? "/teacher" : "/dashboard");
  }, [current, disabledRoute, router]);

  if (!current || current.user.role === "PARENT") return null;
  const isTeacher = current.user.role === "TEACHER";
  if (disabledRoute) return null;

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
      <Link href={isTeacher ? "/teacher" : "/dashboard"} className="brand" aria-label="Умный сад — главная"><span className="brand-mark" aria-hidden="true">✳</span> Умный сад</Link>
      <div className="header-actions">
        <span className="organization-name">{current.organization.name}</span>
        <div className="header-user"><strong>{current.user.username}</strong><span>{ROLE_LABELS[current.user.role] ?? "Пользователь"}</span></div>
        <Button variant="secondary" onClick={() => void logout()} disabled={busy}>{busy ? "Выход..." : "Выйти"}</Button>
      </div>
    </header>
    {error && <div className="shell-alert"><Alert>{error}</Alert></div>}
    <div className="app-body">
      <aside className="sidebar" aria-label="Основное меню">
        {isTeacher ? <TeacherNav /> : <ManagementNav role={current.user.role} />}
      </aside>
      <main className="main-content">{children}</main>
    </div>
  </div>;
}
