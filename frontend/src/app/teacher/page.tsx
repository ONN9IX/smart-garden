"use client";

import { AppShell } from "@/components/layout/app-shell";
import { AuthGate } from "@/features/auth/auth-gate";

export default function TeacherPage() {
  return <AuthGate route="teacher"><AppShell>
    <div className="page-heading">
      <span className="eyebrow">Foundation</span>
      <h1>Кабинет воспитателя</h1>
      <p>Профиль воспитателя подключён. Рабочие разделы появятся на следующем этапе.</p>
    </div>
  </AppShell></AuthGate>;
}
