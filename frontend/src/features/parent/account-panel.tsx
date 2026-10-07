"use client";

import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { guardiansApi } from "@/lib/api/guardians";
import { userMessage } from "@/lib/api/client";
import type { Guardian, InvitationResult, ParentAccountSummary } from "@/types/stage2";

export function AccountPanel({ guardian, onAccountChange }: { guardian: Guardian; onAccountChange: (account: ParentAccountSummary) => void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  async function run(action: () => Promise<InvitationResult | ParentAccountSummary>) {
    if (busy) return; setBusy(true); setError(""); setMessage("");
    try { const result = await action(); if ("role" in result) setMessage(result.status === "sent" ? `Приглашение отправлено. Логин: ${result.username}` : "Доступ создан, но письмо отправить не удалось. Повторите отправку."); else { onAccountChange(result); setMessage("Статус учётной записи изменён."); } }
    catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  }
  const account = guardian.account;
  return <section className="section-space"><h2>Учётная запись родителя</h2>{error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    {!account ? <div className="card section-card"><p>Доступ пока не создан. Родитель задаст пароль по одноразовой ссылке из письма.</p><Button disabled={busy || guardian.status !== "active"} onClick={() => void run(() => guardiansApi.createAccount(guardian.id))}>Создать доступ</Button></div>
      : <div className="card section-card"><p>Логин: <strong>{account.username}</strong></p><p>Статус: {account.status === "active" ? "Активен" : "Заблокирован"}</p><div className="action-row">
        {account.must_change_password && <Button variant="secondary" disabled={busy} onClick={() => void run(() => guardiansApi.resendInvite(guardian.id))}>Отправить приглашение снова</Button>}
        {account.status === "active" ? <Button variant="secondary" disabled={busy} onClick={() => { if (window.confirm("Заблокировать аккаунт родителя?")) void run(() => guardiansApi.blockAccount(guardian.id)); }}>Заблокировать</Button> : <Button variant="secondary" disabled={busy || guardian.status !== "active"} onClick={() => void run(() => guardiansApi.unblockAccount(guardian.id))}>Разблокировать</Button>}
      </div></div>}
  </section>;
}
