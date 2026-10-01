"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { featureEnabled, type ProductFeature } from "@/config/product-features";
import type { Role } from "@/types/auth";

function navClass(active: boolean) { return `nav-item ${active ? "active" : ""}`; }

type NavItem = readonly [href: string, label: string, feature?: ProductFeature];
type NavSection = { label: string; items: readonly NavItem[] };

export function ManagementNav({ role }: { role: Role }) {
  const pathname = usePathname();
  const sections: readonly NavSection[] = [
    {
      label: "Работа",
      items: [
        ["/dashboard", "Главная"],
        ["/attendance", "Посещаемость"],
        ["/schedule", "Расписание"],
        ["/announcements", "Объявления"],
        ["/tasks", "Задачи"],
        ["/communications", "Сообщения"],
        ["/notifications", "Уведомления"],
      ],
    },
    {
      label: "Люди и группы",
      items: [
        ["/children", "Дети"],
        ["/groups", "Группы"],
        ["/guardians", "Родители"],
        ["/employees", "Сотрудники"],
        ["/teachers", "Воспитатели"],
      ],
    },
    {
      label: "Отложено",
      items: [
        ["/incidents", "Происшествия", "incidents"],
        ["/polls", "Опросы", "polls"],
        ["/diary", "Дневник", "diary"],
        ["/document-notices", "Уведомления о документах", "documentNotices"],
        ["/photo-consents", "Согласия на фото", "photos"],
      ],
    },
  ];

  return <>
    <nav>
      {sections.map((section) => {
        const visibleItems = section.items.filter(([, , feature]) => !feature || featureEnabled(feature));
        if (visibleItems.length === 0) return null;
        return <div className="nav-group" key={section.label}>
          <div className="nav-section-title">{section.label}</div>
          {visibleItems.map(([href, label]) => {
            const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
            return <Link key={href} href={href} className={navClass(active)} aria-current={active ? "page" : undefined}>{label}</Link>;
          })}
        </div>;
      })}
      {role === "DIRECTOR" && <div className="nav-group">
        <div className="nav-section-title">Система</div>
        <Link href="/audit" className={navClass(pathname.startsWith("/audit"))} aria-current={pathname.startsWith("/audit") ? "page" : undefined}>Аудит</Link>
        <Link href="/settings" className={navClass(pathname.startsWith("/settings"))} aria-current={pathname.startsWith("/settings") ? "page" : undefined}>Настройки</Link>
      </div>}
    </nav>
    <p className="sidebar-note">{role === "DIRECTOR" ? "Директор: полный управленческий доступ." : "Администратор: операционный доступ без аудита и настроек."}</p>
  </>;
}
