"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { teacherApi } from "@/lib/api/teacher";
import type { Today } from "@/types/teacher";
import { userMessage } from "@/lib/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { employeesApi, type OwnCoachProfile } from "@/lib/api/employees";

export function GymnasticsToday() {
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState<OwnCoachProfile | null | undefined>(undefined);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  async function load() { try { setToday(await teacherApi.today()); setError(""); } catch (e) { setError(userMessage(e, "Не удалось загрузить тренерский день.")); } }
  useEffect(() => { void Promise.resolve().then(async () => { try { const own = await employeesApi.myCoachProfile(); setProfile(own); if (own) await load(); } catch (e) { setError(userMessage(e, "Не удалось проверить тренерский профиль.")); } }); }, []);
  async function createProfile() {
    setBusy(true); setError("");
    try { const own = await employeesApi.createMyCoachProfile({ first_name: firstName, last_name: lastName }); setProfile(own); await load(); }
    catch (e) { setError(userMessage(e, "Не удалось создать тренерский профиль.")); }
    finally { setBusy(false); }
  }
  async function markAll(groupId: string) {
    const roster = await teacherApi.children(groupId);
    if (!roster.length) return;
    setBusy(true); setError("");
    try { await teacherApi.saveGroupDayAttendance({ group_id: groupId, date: today!.date, items: roster.map(child => ({ child_id: child.id, status: "present" })) }); await load(); }
    catch (e) { setError(userMessage(e, "Не удалось сохранить посещаемость.")); }
    finally { setBusy(false); }
  }
  return <main className="page-container"><header><p>Рабочий экран тренера</p><h1>Сегодня</h1><p>{today?.date ?? "Загрузка…"}</p></header>
    {error && <Alert>{error}</Alert>}
    {profile === undefined && <p role="status">Проверяем тренерский профиль…</p>}
    {profile === null && <section className="card"><h2>Создайте свой профиль тренера</h2><p>Используйте минимальные данные для своей карточки сотрудника. Аккаунт и роль не меняются.</p><label>Имя<input required maxLength={100} value={firstName} onChange={event => setFirstName(event.target.value)} /></label><label>Фамилия<input required maxLength={100} value={lastName} onChange={event => setLastName(event.target.value)} /></label><Button disabled={busy || !firstName.trim() || !lastName.trim()} onClick={() => void createProfile()}>{busy ? "Сохраняем…" : "Создать профиль тренера"}</Button></section>}
    {profile && !today && <p>Для тренерского экрана попросите назначить свой профиль в нужные группы. <Link href="/teachers">Перейти к назначениям</Link></p>}
    <div className="today-actions"><Link href="/teacher/schedule">Расписание</Link><Link href="/teacher/communications">Сообщения</Link><Link href="/teacher/attendance">Посещаемость</Link></div>
    <h2>Мои назначенные группы</h2>
    {today?.groups.map(group => { const count = today.attendance.find(a => a.group_id === group.id); const next = today.schedule.find(s => s.group_id === group.id); return <article className="card" key={group.id}>
      <h3>{group.name}</h3><p>{next ? `${next.start_time.slice(0,5)}–${next.end_time.slice(0,5)} · ${next.title}` : "Сегодня нет тренировки в расписании"}</p>
      <p>Спортсменов: {count?.active_children ?? 0} · присутствуют: {count?.present ?? 0} · отсутствуют: {count?.absent ?? 0} · без отметки: {count?.unknown ?? 0}</p>
      <Button disabled={busy || !count?.active_children} onClick={() => void markAll(group.id)}>Отметить всех присутствующими</Button>
      <Link href={`/teacher/attendance?group=${encodeURIComponent(group.id)}`}>Изменить отметки</Link>
    </article>; })}
    {today && today.groups.length === 0 && <p>Нет назначенных активных групп.</p>}
  </main>;
}
