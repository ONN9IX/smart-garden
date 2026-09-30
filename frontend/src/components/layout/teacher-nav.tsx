"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function TeacherNav() {
  const active = usePathname() === "/teacher";
  return <>
    <nav><Link href="/teacher" className={`nav-item ${active ? "active" : ""}`} aria-current={active ? "page" : undefined}>Сегодня</Link></nav>
    <p className="sidebar-note">Разделы кабинета будут добавлены после Foundation.</p>
  </>;
}
