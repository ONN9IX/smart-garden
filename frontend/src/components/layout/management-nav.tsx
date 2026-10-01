"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { featureEnabled, type ProductFeature } from "@/config/product-features";
import type { Role } from "@/types/auth";

function navClass(active: boolean) { return `nav-item ${active ? "active" : ""}`; }

type NavItem = readonly [href: string, label: string, feature?: ProductFeature];

export function ManagementNav({ role }: { role: Role }) {
  const pathname = usePathname();
  const links: readonly NavItem[] = [
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
    ["/incidents", "Происшествия", "incidents"],
    ["/polls", "Опросы", "polls"],
    ["/communications", "Сообщения"],
    ["/diary", "Дневник", "diary"],
    ["/notifications", "Уведомления"],
    ["/document-notices", "Уведомления о документах", "documentNotices"],
    ["/photo-consents", "Согласия на фото", "photos"],
  ];

  return <>
    <nav>
      {links.filter(([, , feature]) => !feature || featureEnabled(feature)).map(([href, label]) => {
        const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
        return <Link key={href} href={href} className={navClass(active)} aria-current={active ? "page" : undefined}>{label}</Link>;
      })}
      {role === "DIRECTOR" && <Link href="/audit" className={navClass(pathname.startsWith("/audit"))} aria-current={pathname.startsWith("/audit") ? "page" : undefined}>Аудит</Link>}
      {role === "DIRECTOR" && <Link href="/settings" className={navClass(pathname.startsWith("/settings"))} aria-current={pathname.startsWith("/settings") ? "page" : undefined}>Настройки</Link>}
    </nav>
    <p className="sidebar-note">{role === "DIRECTOR" ? "Директор: полный управленческий доступ." : "Администратор: операционный доступ без аудита и настроек."}</p>
  </>;
}
