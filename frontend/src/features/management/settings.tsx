"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";

export function SettingsPage() {
  return <AuthGate route="director"><AppShell><SettingsContent /></AppShell></AuthGate>;
}

function SettingsContent() {
  const { refresh } = useAuth();
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const value = await managementApi.settings();
      setName(value.name);
      setTimezone(value.timezone);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setMessage("");
    try {
      const value = await managementApi.updateSettings({ name: name.trim(), timezone: timezone.trim() });
      setName(value.name); setTimezone(value.timezone);
      await refresh();
      setMessage("Настройки сохранены.");
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Директор</span><h1>Настройки организации</h1><p>Название сада и календарный часовой пояс.</p></div>
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    {loading ? <Loading /> : <form className="card section-card" onSubmit={(event) => void save(event)}>
      <div className="form-grid">
        <label>Название <Input required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>Часовой пояс IANA <Input required maxLength={64} value={timezone} onChange={(event) => setTimezone(event.target.value)} /></label>
      </div>
      <Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</Button>
    </form>}
  </>;
}
