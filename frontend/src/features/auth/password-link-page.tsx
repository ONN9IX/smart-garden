"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { PasswordInput } from "@/components/ui/password-input";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";

export function PasswordLinkPage({ purpose }: { purpose: "activation" | "reset" }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const fragmentToken = fragment.get("token");
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    void Promise.resolve().then(() => {
      setToken(fragmentToken);
      setReady(true);
    });
  }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!token || busy) { setError("Ссылка недействительна или срок её действия истёк."); return; }
    if (password !== confirmation) { setError("Пароли не совпадают."); return; }
    setBusy(true); setError("");
    try {
      if (purpose === "activation") await authApi.activate(token, password);
      else await authApi.resetPassword(token, password);
      setToken(null);
      router.replace("/login");
    } catch (reason) { setError(userMessage(reason)); setBusy(false); }
  }
  return <main className="center-screen"><section className="auth-card">
    <div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> ПРОМАКС</div>
    <h1>{purpose === "activation" ? "Активировать доступ" : "Новый пароль"}</h1>
    {!ready ? <p>Проверяем ссылку…</p> : <form onSubmit={(event) => void submit(event)}>
      <FormField id="new-password" label="Новый пароль"><PasswordInput id="new-password" autoComplete="new-password" minLength={10} required value={password} onChange={(event) => setPassword(event.target.value)} /></FormField>
      <FormField id="confirm-password" label="Повторите новый пароль"><PasswordInput id="confirm-password" autoComplete="new-password" minLength={10} required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></FormField>
      {error && <Alert>{error}</Alert>}<Button className="full-width" disabled={busy}>{busy ? "Сохранение…" : "Сохранить пароль"}</Button>
    </form>}
    <p><Link className="text-link" href="/login">Вернуться ко входу</Link></p>
  </section></main>;
}
