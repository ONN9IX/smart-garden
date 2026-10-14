"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Role } from "@/types/auth";
import { useAuth } from "@/features/auth/auth-provider";
import { organizationTerms } from "@/lib/organization-terminology";

function navClass(active: boolean) { return `nav-item ${active ? "active" : ""}`; }

type NavItem = readonly [href: string, label: string];
type NavSection = { label: string; items: readonly NavItem[] };

export function ManagementNav({ role }: { role: Role }) {
  const { current } = useAuth();
  const terms = organizationTerms(current?.organization.operating_profile ?? "KINDERGARTEN");
  const pathname = usePathname();
  const sections: readonly NavSection[] = [
    {
      label: current?.organization.operating_profile === "GYMNASTICS" ? "Спортсмены и группы" : "Люди и группы",
      items: [
        ["/groups", "Группы"],
        ["/children", current?.organization.operating_profile === "GYMNASTICS" ? "Спортсмены" : "Дети"],
        ["/guardians", "Родители"],
        ["/employees", "Сотрудники"],
        ["/access-accounts", "Доступ и аккаунты"],
      ],
    },
    {
      label: current?.organization.operating_profile === "GYMNASTICS" ? "Работа секции" : "Работа сада",
      items: [
        ...(current?.organization.operating_profile === "GYMNASTICS" && role === "DIRECTOR" ? [["/teacher/attendance", "Посещаемость"] as const] : [["/attendance", "Посещаемость"] as const]),
        ["/schedule", terms.schedule],
        ["/tasks", "Задачи"],
      ],
    },
    {
      label: "Связь",
      items: [
        ["/communications", "Сообщения"],
        ["/announcements", "Объявления"],
      ],
    },
  ];

  return <>
    <nav>
      <Link href="/dashboard" className={navClass(pathname === "/dashboard")}
        aria-current={pathname === "/dashboard" ? "page" : undefined}>Сегодня</Link>
      {sections.map((section) => {
        const visibleItems = section.items;
        if (visibleItems.length === 0) return null;
        return <div className="nav-group" key={section.label}>
          <div className="nav-section-title">{section.label}</div>
          {visibleItems.map(([href, label]) => {
            const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
            return <Link key={href} href={href} className={navClass(active)} aria-current={active ? "page" : undefined}>{label}</Link>;
          })}
        </div>;
      })}
      <div className="nav-group">
        <div className="nav-section-title">Контроль</div>
        <Link href="/notifications" className={navClass(pathname.startsWith("/notifications"))} aria-current={pathname.startsWith("/notifications") ? "page" : undefined}>Контроль и уведомления</Link>
        {role === "DIRECTOR" && <Link href="/audit" className={navClass(pathname.startsWith("/audit"))} aria-current={pathname.startsWith("/audit") ? "page" : undefined}>Журнал действий</Link>}
      </div>
      {role === "DIRECTOR" && <Link href="/settings" className={navClass(pathname.startsWith("/settings"))} aria-current={pathname.startsWith("/settings") ? "page" : undefined}>Настройки</Link>}
      {role === "DIRECTOR" && <Link href="/initial-setup" className={navClass(pathname.startsWith("/initial-setup"))} aria-current={pathname.startsWith("/initial-setup") ? "page" : undefined}>Первоначальная настройка</Link>}
    </nav>
    <p className="sidebar-note">{role === "DIRECTOR" ? (current?.organization.operating_profile === "GYMNASTICS" ? "Управление спортивной секцией" : "Управление детским садом") : (current?.organization.operating_profile === "GYMNASTICS" ? "Работа спортивной секции" : "Операционная работа детского сада")}</p>
  </>;
}
