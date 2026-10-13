"use client";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { GymnasticsToday } from "@/features/management/gymnastics-today";
import { TodayDashboard } from "@/features/teacher/today-dashboard";

export default function TeacherPage() {
  const { current } = useAuth();
  const gymnasticsOwner = current?.user.role === "DIRECTOR" && current.organization.operating_profile === "GYMNASTICS";
  if (!gymnasticsOwner) return <TodayDashboard />;
  return <AuthGate route="teacher"><AppShell><GymnasticsToday /></AppShell></AuthGate>;
}
