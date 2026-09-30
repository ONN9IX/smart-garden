"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Role } from "@/types/auth";

const futureSections = ["Настройки"];

function navClass(active: boolean) { return `nav-item ${active ? "active" : ""}`; }

export function ManagementNav({ role }: { role: Role }) {
  const pathname = usePathname();
  return <>
    <nav>
      <Link href="/dashboard" className={navClass(pathname === "/dashboard")} aria-current={pathname === "/dashboard" ? "page" : undefined}>Главная</Link>
      <Link href="/children" className={navClass(pathname.startsWith("/children"))} aria-current={pathname.startsWith("/children") ? "page" : undefined}>Дети</Link>
      <Link href="/groups" className={navClass(pathname.startsWith("/groups"))} aria-current={pathname.startsWith("/groups") ? "page" : undefined}>Группы</Link>
      <Link href="/guardians" className={navClass(pathname.startsWith("/guardians"))} aria-current={pathname.startsWith("/guardians") ? "page" : undefined}>Родители</Link>
      <Link href="/employees" className={navClass(pathname.startsWith("/employees"))} aria-current={pathname.startsWith("/employees") ? "page" : undefined}>Сотрудники</Link>
      <Link href="/attendance" className={navClass(pathname.startsWith("/attendance"))} aria-current={pathname.startsWith("/attendance") ? "page" : undefined}>Посещаемость</Link>
      <Link href="/announcements" className={navClass(pathname.startsWith("/announcements"))} aria-current={pathname.startsWith("/announcements") ? "page" : undefined}>Объявления</Link>
      {role === "DIRECTOR" && <Link href="/audit" className={navClass(pathname.startsWith("/audit"))} aria-current={pathname.startsWith("/audit") ? "page" : undefined}>Аудит</Link>}
      {futureSections.map((section) => <span key={section} className="nav-item disabled" aria-disabled="true" title="Раздел будет реализован на следующем этапе">{section}</span>)}
    </nav>
    <p className="sidebar-note">Настройки появятся на следующих этапах.</p>
  </>;
}
