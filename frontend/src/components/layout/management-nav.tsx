"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Role } from "@/types/auth";

function navClass(active: boolean) { return `nav-item ${active ? "active" : ""}`; }

export function ManagementNav({ role }: { role: Role }) {
  const pathname = usePathname();
  const links = [
    ["/dashboard", "Главная"],
    ["/children", "Дети"],
    ["/groups", "Группы"],
    ["/guardians", "Родители"],
    ["/employees", "Сотрудники"],
    ["/teachers", "Воспитатели"],
    ["/attendance", "Посещаемость"],
    ["/schedule", "Расписание"],
    ["/announcements", "Объявления"],
    ["/tasks", "Задачи"],
    ["/incidents", "Происшествия"],
    ["/polls", "Опросы"],
    ["/communications", "Сообщения"],
    ["/diary", "Дневник"],
    ["/notifications", "Уведомления"],
    ["/document-notices", "Уведомления о документах"],
    ["/photo-consents", "Согласия на фото"],
  ] as const;

  return <>
    <nav>
      {links.map(([href, label]) => {
        const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
        return <Link key={href} href={href} className={navClass(active)} aria-current={active ? "page" : undefined}>{label}</Link>;
      })}
      {role === "DIRECTOR" && <Link href="/audit" className={navClass(pathname.startsWith("/audit"))} aria-current={pathname.startsWith("/audit") ? "page" : undefined}>Аудит</Link>}
      {role === "DIRECTOR" && <Link href="/settings" className={navClass(pathname.startsWith("/settings"))} aria-current={pathname.startsWith("/settings") ? "page" : undefined}>Настройки</Link>}
    </nav>
    <p className="sidebar-note">{role === "DIRECTOR" ? "Директор: полный управленческий доступ." : "Администратор: операционный доступ без аудита и настроек."}</p>
  </>;
}
