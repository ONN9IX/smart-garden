"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function TeacherNav() {
  const pathname = usePathname();
  const items = [
    ["/teacher", "Сегодня"], ["/teacher/groups", "Мои группы"],
    ["/teacher/attendance", "Посещаемость"], ["/teacher/schedule", "Расписание"],
    ["/teacher/communications", "Родители и сообщения"], ["/teacher/more", "Ещё"],
  ];
  return <>
    <nav>{items.map(([href, label]) => {
      const active = href === "/teacher" ? pathname === href : pathname.startsWith(href);
      return <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`} aria-current={active ? "page" : undefined}>{label}</Link>;
    })}</nav>
    <p className="sidebar-note">Только назначенные группы и рабочий контекст.</p>
  </>;
}
