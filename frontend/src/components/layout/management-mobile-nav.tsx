"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { Role } from "@/types/auth";

const items = [
  ["/dashboard", "Сегодня", "◷"],
  ["/groups", "Люди", "♧"],
  ["/attendance", "Работа", "✓"],
  ["/communications", "Связь", "✉"],
] as const;

export function ManagementMobileNav({ role, username, roleLabel }: {
  role: Extract<Role, "DIRECTOR" | "ADMIN">;
  username: string;
  roleLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return <>
    {open && <div className="mobile-more-panel" id="management-more-panel">
      <Link href="/access-accounts" onClick={() => setOpen(false)}>Доступ и аккаунты</Link>
      {role === "DIRECTOR" ? <>
        <Link href="/notifications" onClick={() => setOpen(false)}>Уведомления</Link>
        <Link href="/audit" onClick={() => setOpen(false)}>Журнал действий</Link>
        <Link href="/settings" onClick={() => setOpen(false)}>Настройки</Link>
        <div className="mobile-account-context"><strong>{username}</strong><span>{roleLabel}</span></div>
      </> : <div className="mobile-account-context"><strong>Аккаунт</strong><span>{username} · {roleLabel}</span></div>}
    </div>}
    <nav className="management-mobile-nav" aria-label="Мобильная навигация">
      {items.map(([href, label, icon]) => {
        const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href))
          || (href === "/attendance" && ["/schedule", "/tasks"].some((route) => pathname.startsWith(route)));
        return <Link href={href} key={href} className={`mobile-nav-item${active ? " active" : ""}`}
          aria-current={active ? "page" : undefined}>
        <span aria-hidden="true">{icon}</span><span>{label}</span>
      </Link>;
      })}
      <button type="button" className="mobile-nav-item" aria-expanded={open}
        aria-controls="management-more-panel" onClick={() => setOpen((value) => !value)}>
        <span aria-hidden="true">···</span><span>Ещё</span>
      </button>
    </nav>
  </>;
}
