"use client";

import { useEffect, useRef, useState } from "react";
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
  const token = useRef<string | null>(null);
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    token.current = fragment.get("token");
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    void Promise.resolve().then(() => setReady(true));
    return () => { token.current = null; };
  }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!token.current || busy) { setError("Ссылка недействительна или срок её действия истёк."); return; }
    setBusy(true); setError("");
    try {
      if (purpose === "activation") await authApi.activate(token.current, password);
      else await authApi.resetPassword(token.current, password);
      token.current = null;
      router.replace("/login");
    } catch (reason) { setError(userMessage(reason)); setBusy(false); }
  }
  return <main className="center-screen"><section className="auth-card">
    <div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> ПРОМАКС</div>
    <h1>{purpose === "activation" ? "Активировать доступ" : "Новый пароль"}</h1>
    {!ready ? <p>Проверяем ссылку…</p> : <form onSubmit={(event) => void submit(event)}>
      <FormField id="new-password" label="Новый пароль"><PasswordInput id="new-password" autoComplete="new-password" minLength={10} required value={password} onChange={(event) => setPassword(event.target.value)} /></FormField>
      {error && <Alert>{error}</Alert>}<Button className="full-width" disabled={busy}>{busy ? "Сохранение…" : "Сохранить пароль"}</Button>
    </form>}
    <p><Link className="text-link" href="/login">Вернуться ко входу</Link></p>
  </section></main>;
}
