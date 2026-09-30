"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AuthGate } from "@/features/auth/auth-gate";

export const fullName = (item: { first_name: string; last_name: string; middle_name?: string | null }) =>
  [item.last_name, item.first_name, item.middle_name].filter(Boolean).join(" ");

export function useQueryParam(name: string, setValue: (value: string) => void) {
  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get(name);
    if (value) setValue(value);
  }, [name, setValue]);
}

export function SectionError({ error, retry }: { error: string; retry?: () => void }) {
  if (!error) return null;
  return <div className="section-space"><Alert>{error}</Alert>{retry && <Button variant="secondary" onClick={retry}>Повторить</Button>}</div>;
}

export function ManagerPage({ children }: { children: ReactNode }) {
  return <AuthGate route="dashboard"><AppShell>{children}</AppShell></AuthGate>;
}
