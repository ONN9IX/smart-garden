"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "@/features/teacher/cabinet.module.css";
import { useAuth } from "@/features/auth/auth-provider";
import { organizationTerms } from "@/lib/organization-terminology";

export function TeacherNav() {
  const { current } = useAuth();
  const terms = organizationTerms(current?.organization.operating_profile ?? "KINDERGARTEN");
  const pathname = usePathname();
  const items = [
    ["/teacher", "Сегодня"],
    ["/teacher/groups", `Мои ${terms.groups}`],
    ["/teacher/attendance", terms.attendance],
    ["/teacher/schedule", terms.schedule],
    ["/teacher/communications", "Сообщения"],
    ["/teacher/announcements", "Объявления"],
    ["/teacher/more", "Задачи и уведомления"],
  ];
  return <>
    <nav className={styles.teacherNav} aria-label="Разделы воспитателя">{items.map(([href, label]) => {
      const active = href === "/teacher" ? pathname === href : pathname.startsWith(href);
      return <Link key={href} href={href} className={`nav-item ${active ? "active" : ""}`} aria-current={active ? "page" : undefined}>{label}</Link>;
    })}</nav>
    <p className={styles.navNote}>Только явно назначенные группы и рабочий контекст.</p>
  </>;
}
