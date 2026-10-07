"use client";

import { AppShell } from "@/components/layout/app-shell";
import { AuthGate } from "@/features/auth/auth-gate";
import { ManagementTodayPanel } from "@/features/management/today";

export function DashboardPage() {
  return <AuthGate route="dashboard"><AppShell><ManagementTodayPanel /></AppShell></AuthGate>;
}
