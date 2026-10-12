"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { OrganizationNotificationSettings, SecurityStatus } from "@/types/management";

export function SettingsPage() {
  return <AuthGate route="director"><AppShell><SettingsContent /></AppShell></AuthGate>;
}

function SettingsContent() {
  const { refresh } = useAuth();
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState("");
  const [savedTimezone, setSavedTimezone] = useState("");
  const [notificationSettings, setNotificationSettings] = useState<OrganizationNotificationSettings | null>(null);
  const [security, setSecurity] = useState<SecurityStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [value, preferences, securityStatus] = await Promise.all([
        managementApi.settings(), managementApi.notificationSettings(), managementApi.securityStatus(),
      ]);
      setName(value.name);
      setTimezone(value.timezone); setSavedTimezone(value.timezone);
      setNotificationSettings(preferences); setSecurity(securityStatus);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (timezone.trim() !== savedTimezone && !window.confirm(
      "Изменение часового пояса повлияет на «Сегодня», время отсечения посещаемости и расписания. Продолжить?",
    )) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const value = await managementApi.updateSettings({ name: name.trim(), timezone: timezone.trim() });
      setName(value.name); setTimezone(value.timezone); setSavedTimezone(value.timezone);
      await refresh();
      setMessage("Настройки сохранены.");
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  async function saveNotifications(event: React.FormEvent) {
    event.preventDefault();
    if (!notificationSettings) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const value = await managementApi.updateNotificationSettings(notificationSettings);
      setNotificationSettings(value); setMessage("Настройки уведомлений сохранены.");
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Директор</span><h1>Настройки организации</h1><p>Организация, уведомления и состояние доступа.</p></div>
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    {loading ? <Loading /> : <div className="settings-sections"><form className="card section-card" onSubmit={(event) => void save(event)}>
      <h2>Организация</h2>
      <div className="form-grid">
        <label>Название <Input required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>Часовой пояс IANA <Input required maxLength={64} value={timezone} onChange={(event) => setTimezone(event.target.value)} /></label>
      </div>
      <Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</Button>
    </form>
      {notificationSettings && <form className="card section-card" onSubmit={(event) => void saveNotifications(event)}>
        <h2>Уведомления</h2>
        <label className="settings-check"><input type="checkbox" checked={notificationSettings.show_informational_notifications}
          onChange={(event) => setNotificationSettings({ ...notificationSettings, show_informational_notifications: event.target.checked })} /> Показывать информационные уведомления</label>
        <label>Время проверки посещаемости<Input type="time" value={notificationSettings.attendance_checkpoint_time?.slice(0, 5) || ""}
          onChange={(event) => setNotificationSettings({ ...notificationSettings, attendance_checkpoint_time: event.target.value || null })} /></label>
        <p className="muted">Пустое значение означает проверку без отсрочки. Время сада: {savedTimezone}.</p>
        <label className="settings-check"><input type="checkbox" checked={notificationSettings.schedule_missing_alert_enabled}
          onChange={(event) => setNotificationSettings({ ...notificationSettings, schedule_missing_alert_enabled: event.target.checked })} /> Напоминать об отсутствующем расписании</label>
        <Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить уведомления"}</Button>
      </form>}
      <section className="card section-card"><h2>Доступы и аккаунты</h2><p>Управление аккаунтами и приглашениями.</p>
        <Link href="/access-accounts">Открыть доступы и аккаунты →</Link></section>
      <section className="card section-card"><h2>Безопасность</h2>
        <p>Заблокированных аккаунтов: {security?.blocked_accounts ?? 0}</p>
        <p>Неудачных или истёкших приглашений родителям: {security?.failed_or_expired_parent_invites ?? 0}</p>
        <Link href="/audit">Открыть журнал действий →</Link></section>
      <section className="card section-card"><h2>Интеграции</h2><p>Нет подключённых интеграций.</p></section>
      <section className="card section-card"><h2>Приватность данных</h2>
        <p>В разработке и тестировании используются синтетические данные. Работа с реальными персональными данными требует отдельного согласования.</p></section>
    </div>}
  </>;
}
