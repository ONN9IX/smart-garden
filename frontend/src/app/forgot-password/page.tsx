"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api/auth";

const GENERIC = "Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email.";
const REQUEST_ERROR = "Не удалось отправить запрос. Проверьте подключение и попробуйте ещё раз.";
export default function ForgotPasswordPage() {
  const submitting = useRef(false);
  const [identifier, setIdentifier] = useState(""); const [busy, setBusy] = useState(false); const [done, setDone] = useState(false); const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      await authApi.forgotPassword(identifier.trim());
      setDone(true);
    } catch {
      // Keep account existence private and handle rejected fetches without an unhandled Promise.
      setError(REQUEST_ERROR);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  return <main className="center-screen"><section className="auth-card"><div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> ПРОМАКС</div><h1>Восстановление доступа</h1>
    {done ? <Alert tone="success">{GENERIC}</Alert> : <form onSubmit={(event) => void submit(event)}><FormField id="identifier" label="Логин или email"><Input id="identifier" required autoFocus value={identifier} onChange={(event) => setIdentifier(event.target.value)} /></FormField>{error && <Alert>{error}</Alert>}<Button className="full-width" disabled={busy}>{busy ? "Отправка…" : "Отправить ссылку"}</Button></form>}
    <p><Link className="text-link" href="/login">Вернуться ко входу</Link></p></section></main>;
}
