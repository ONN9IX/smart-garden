"use client";

/** Username/password login; identity and role are always refreshed from /auth/me. */
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";

export default function LoginPage() {
  return <AuthGate route="login"><LoginForm /></AuthGate>;
}

function LoginForm() {
  const router = useRouter();
  const { refresh } = useAuth();
  const submitting = useRef(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      await authApi.login(username.trim(), password);
      const current = await refresh();
      if (!current) throw new Error("No session after login");
      router.replace(current.user.must_change_password ? "/change-password" : current.user.role === "PARENT" ? "/parent" : "/dashboard");
    } catch (reason) {
      setError(userMessage(reason, "Не удалось выполнить вход. Попробуйте ещё раз."));
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return <main className="center-screen"><section className="auth-card" aria-labelledby="login-title">
    <div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> Умный сад</div>
    <h1 id="login-title">Вход в систему</h1>
    <p className="muted">Рабочий кабинет детского сада</p>
    <form onSubmit={(event) => void submit(event)}>
      <FormField id="username" label="Логин"><Input id="username" name="username" autoComplete="username" autoFocus required value={username} onChange={(event) => setUsername(event.target.value)} /></FormField>
      <FormField id="password" label="Пароль"><PasswordInput id="password" name="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></FormField>
      {error && <Alert>{error}</Alert>}
      <Button className="full-width" type="submit" disabled={busy}>{busy ? "Вход..." : "Войти"}</Button>
    </form>
  </section></main>;
}
