"use client";

/** Mandatory first-login password change; the backend rotates the session cookie. */
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { authApi } from "@/lib/api/auth";
import { userMessage } from "@/lib/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { PasswordInput } from "@/components/ui/password-input";

export default function ChangePasswordPage() {
  return <AuthGate route="change-password"><PasswordForm /></AuthGate>;
}

function PasswordForm() {
  const router = useRouter();
  const { refresh, clear } = useAuth();
  const submitting = useRef(false);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    if (password.length < 10) { setError("Новый пароль должен содержать не менее 10 символов."); return; }
    if (password !== confirmation) { setError("Пароли не совпадают."); return; }
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      await authApi.changePassword(password);
      setPassword("");
      setConfirmation("");
      const current = await refresh();
      if (!current || current.user.must_change_password) {
        clear();
        router.replace("/login");
        return;
      }
      router.replace(current.user.role === "PARENT" ? "/parent" : "/dashboard");
    } catch (reason) {
      setError(userMessage(reason, "Не удалось изменить пароль. Попробуйте ещё раз."));
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  return <main className="center-screen"><section className="auth-card" aria-labelledby="password-title">
    <div className="auth-brand"><span className="brand-mark" aria-hidden="true">✳</span> Умный сад</div>
    <h1 id="password-title">Смените временный пароль</h1>
    <p className="muted">Придумайте новый пароль длиной не менее 10 символов, чтобы продолжить работу.</p>
    <form onSubmit={(event) => void submit(event)}>
      <FormField id="new-password" label="Новый пароль"><PasswordInput id="new-password" name="new-password" autoComplete="new-password" required minLength={10} value={password} onChange={(event) => setPassword(event.target.value)} /></FormField>
      <FormField id="confirm-password" label="Повторите новый пароль"><PasswordInput id="confirm-password" name="confirm-password" autoComplete="new-password" required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></FormField>
      {error && <Alert>{error}</Alert>}
      <Button className="full-width" type="submit" disabled={busy}>{busy ? "Сохранение..." : "Сохранить пароль"}</Button>
    </form>
  </section></main>;
}
