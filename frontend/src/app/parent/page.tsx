"use client";

/** Technical PARENT landing: only server-confirmed identity and logout are shown. */
import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export default function ParentPage() {
  return <AuthGate route="parent"><ParentContent /></AuthGate>;
}

function ParentContent() {
  const { current, clear } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!current || current.user.role !== "PARENT") return null;
  async function logout() {
    setBusy(true);
    try {
      await authApi.logout();
      clear();
      router.replace("/login");
    } catch (reason) {
      setError(userMessage(reason));
      setBusy(false);
    }
  }
  return <main className="center-screen"><section className="card narrow">
    <div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> Умный сад</div>
    <h1>Кабинет родителя</h1>
    <p>Родительский кабинет пока недоступен в этой версии.</p>
    <p>Пользователь: {current.user.username}</p><p>Детский сад: {current.organization.name}</p><p>Роль: Родитель</p>
    {error && <Alert>{error}</Alert>}
    <Button onClick={() => void logout()} disabled={busy}>Выйти</Button>
  </section></main>;
}
