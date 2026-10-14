"use client";

import { AppShell } from "@/components/layout/app-shell";
import { AuthGate } from "@/features/auth/auth-gate";
import { ManagementTodayPanel } from "@/features/management/today";
import { GymnasticsToday } from "@/features/management/gymnastics-today";
import { useAuth } from "@/features/auth/auth-provider";

export function DashboardPage() {
  const { current } = useAuth();
  const gymCoach = current?.user.role === "DIRECTOR" && current.organization.operating_profile === "GYMNASTICS";
  return <AuthGate route="dashboard"><AppShell>{gymCoach ? <GymnasticsToday /> : <ManagementTodayPanel />}</AppShell></AuthGate>;
}
