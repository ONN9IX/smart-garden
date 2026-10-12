"use client";
import { FormEvent, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AuthProvider } from "@/features/auth/auth-provider";
import { platformApi } from "@/lib/api/platform";

/** Tenant AuthProvider is never mounted on platform routes. */
export function SessionBoundary({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return path === "/platform" || path.startsWith("/platform/") ? (
    children
  ) : (
    <AuthProvider>{children}</AuthProvider>
  );
}

export function PlatformLogin() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [mfa, setMfa] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      if (!mfa) {
        await platformApi.login(username, password);
        setPassword("");
        setMfa(true);
      } else {
        await platformApi.verify(code);
        setCode("");
        router.replace("/platform");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Вход недоступен.");
    } finally {
      setBusy(false);
      setCode("");
    }
  }
  return (
    <main className="center-screen">
      <section className="auth-card">
        <h1>Владелец платформы ПРОМАКС</h1>
        <p>Отдельный вход с обязательным MFA.</p>
        {error && <p role="alert">{error}</p>}
        <form
          className="platform-form"
          onSubmit={(event) => void submit(event)}
        >
          {!mfa ? (
            <>
              <label>
                Логин
                <input
                  autoComplete="username"
                  required
                  maxLength={64}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
              </label>
              <label>
                Пароль
                <input
                  type="password"
                  autoComplete="current-password"
                  required
                  maxLength={128}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>
            </>
          ) : (
            <label>
              Код MFA
              <input
                autoComplete="one-time-code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                required
                maxLength={6}
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
            </label>
          )}
          <button className="button" disabled={busy}>
            {busy ? "Проверка…" : mfa ? "Подтвердить MFA" : "Продолжить"}
          </button>
          {mfa && (
            <button
              type="button"
              className="button secondary"
              disabled={busy}
              onClick={() => {
                platformApi.clear();
                setMfa(false);
                setError("");
              }}
            >
              Начать вход заново
            </button>
          )}
        </form>
        <p>
          Настройка и восстановление MFA выполняются через защищённый процесс
          администратора.
        </p>
      </section>
    </main>
  );
}
