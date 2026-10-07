"use client";

import { useState } from "react";
import Link from "next/link";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api/auth";

const GENERIC = "Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email.";
export default function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState(""); const [busy, setBusy] = useState(false); const [done, setDone] = useState(false);
  async function submit(event: React.FormEvent) { event.preventDefault(); setBusy(true); try { await authApi.forgotPassword(identifier.trim()); } finally { setBusy(false); setDone(true); } }
  return <main className="center-screen"><section className="auth-card"><div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> ПРОМАКС</div><h1>Восстановление доступа</h1>
    {done ? <Alert tone="success">{GENERIC}</Alert> : <form onSubmit={(event) => void submit(event)}><FormField id="identifier" label="Логин или email"><Input id="identifier" required autoFocus value={identifier} onChange={(event) => setIdentifier(event.target.value)} /></FormField><Button className="full-width" disabled={busy}>{busy ? "Отправка…" : "Отправить ссылку"}</Button></form>}
    <p><Link className="text-link" href="/login">Вернуться ко входу</Link></p></section></main>;
}
