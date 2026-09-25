"use client";

/**
 * PARENT account lifecycle. Plaintext temporary credentials exist only in
 * component memory until the one-time card is closed or the page unmounts.
 */
import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { guardiansApi } from "@/lib/api/guardians";
import { userMessage } from "@/lib/api/client";
import type { Guardian, ParentAccountSummary, TemporaryCredentials } from "@/types/stage2";

export function AccountPanel({ guardian, onAccountChange }: {
  guardian: Guardian;
  onAccountChange: (account: ParentAccountSummary) => void;
}) {
  const [credentials, setCredentials] = useState<TemporaryCredentials | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function run(action: () => Promise<TemporaryCredentials | ParentAccountSummary>) {
    if (busy) return;
    setBusy(true); setError(""); setMessage(""); setCredentials(null);
    try {
      const result = await action();
      if ("temporary_password" in result) {
        onAccountChange(result.account);
        setCredentials(result);
      } else {
        onAccountChange(result);
        setMessage("Статус учётной записи изменён.");
      }
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  const account = guardian.account;
  return <section className="section-space"><h2>Учётная запись родителя</h2>
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    {credentials && <div className="card section-card credential-card" role="status">
      <h3>Временные данные для входа</h3>
      <p>Пароль показывается только сейчас. Передайте его родителю безопасным способом.</p>
      <p>Логин: <strong>{credentials.account.username}</strong></p>
      <p>Временный пароль: <strong className="credential-value">{credentials.temporary_password}</strong></p>
      <Button variant="secondary" onClick={() => setCredentials(null)}>Закрыть и скрыть пароль</Button>
    </div>}
    {!account ? <div className="card section-card"><p>Учётная запись пока не создана.</p>
      <Button disabled={busy || guardian.status !== "active"} onClick={() => void run(() => guardiansApi.createAccount(guardian.id))}>Создать учётную запись родителя</Button>
    </div> : <div className="card section-card">
      <p>Логин: <strong>{account.username}</strong></p>
      <p>Статус: {account.status === "active" ? "Активна" : "Заблокирована"}</p>
      <p>Смена временного пароля: {account.must_change_password ? "требуется" : "выполнена"}</p>
      <div className="action-row">
        <Button variant="secondary" disabled={busy} onClick={() => { if (window.confirm("Сбросить пароль? Все текущие сеансы родителя завершатся.")) void run(() => guardiansApi.resetPassword(guardian.id)); }}>Сбросить пароль</Button>
        {account.status === "active"
          ? <Button variant="secondary" disabled={busy} onClick={() => { if (window.confirm("Заблокировать аккаунт родителя?")) void run(() => guardiansApi.blockAccount(guardian.id)); }}>Заблокировать</Button>
          : <Button variant="secondary" disabled={busy || guardian.status !== "active"} onClick={() => void run(() => guardiansApi.unblockAccount(guardian.id))}>Разблокировать</Button>}
      </div>
    </div>}
  </section>;
}
