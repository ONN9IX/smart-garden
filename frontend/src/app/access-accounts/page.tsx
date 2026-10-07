"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { accountAccessApi, type AccessItem, type AccessSections, type BulkResponse } from "@/lib/api/account-access";
import { guardiansApi } from "@/lib/api/guardians";
import { employeesApi } from "@/lib/api/employees";
import { userMessage } from "@/lib/api/client";

const labels = { no_account: "Нет аккаунта", invited: "Приглашение отправлено", delivery_failed: "Ошибка отправки", invite_expired: "Срок приглашения истёк", activated: "Активирован", blocked: "Заблокирован" } as const;
const sections: Array<[keyof AccessSections, string]> = [["parents", "Родители"], ["teachers", "Воспитатели"], ["administrators", "Администраторы"], ["other_employees", "Прочие сотрудники"], ["blocked", "Заблокированные"]];

function Row({ item, selected, toggle, director, busy, act }: { item: AccessItem; selected: boolean; toggle?: () => void; director: boolean; busy: boolean; act: (operation: () => Promise<unknown>, confirmation?: string) => void }) {
  const parent = item.profile_type === "guardian";
  const mayManage = parent || director;
  const invite = item.status === "no_account" ? () => guardiansApi.createAccount(item.profile_id) : () => parent ? guardiansApi.resendInvite(item.profile_id) : employeesApi.resendInvite(item.profile_id, item.role as "TEACHER" | "ADMIN");
  const canInviteHere = mayManage && (parent || Boolean(item.role)) && ["no_account", "invited", "delivery_failed", "invite_expired"].includes(item.status);
  return <li className="card section-card">{toggle && <label><input type="checkbox" checked={selected} onChange={toggle} /> Выбрать</label>}<h3>{item.full_name}</h3><p>{item.context}{item.groups.length ? ` · ${item.groups.join(", ")}` : ""}</p><p>Статус: <strong>{labels[item.status]}</strong></p><p>Логин: {item.username || "—"} · Email: {item.masked_email || "—"}</p>{item.last_login_at && <p className="muted">Последний вход: {new Date(item.last_login_at).toLocaleString("ru-RU")}</p>}<div className="action-row"><Link className="button button-secondary" href={parent ? `/guardians/${item.profile_id}` : `/employees/${item.profile_id}`}>{!parent && item.status === "no_account" && director ? "Открыть профиль и выбрать роль" : "Открыть профиль"}</Link>{canInviteHere && <Button variant="secondary" disabled={busy} onClick={() => act(invite)}>{item.status === "no_account" ? "Создать доступ" : "Отправить приглашение снова"}</Button>}{mayManage && item.username && item.status !== "blocked" && <Button variant="secondary" disabled={busy} onClick={() => act(() => parent ? guardiansApi.blockAccount(item.profile_id) : employeesApi.block(item.profile_id), "Заблокировать аккаунт и завершить все действующие сеансы?")}>Заблокировать</Button>}{mayManage && item.status === "blocked" && <Button variant="secondary" disabled={busy} onClick={() => act(() => parent ? guardiansApi.unblockAccount(item.profile_id) : employeesApi.unblock(item.profile_id))}>Разблокировать</Button>}{director && item.username && <Button variant="secondary" disabled={busy} onClick={() => act(() => accountAccessApi.revokeSessions(item.profile_type, item.profile_id), "Завершить все действующие сеансы этого аккаунта?")}>Завершить все сеансы</Button>}{director && item.profile_type === "employee" && item.role && <Button variant="secondary" disabled={busy} onClick={() => { const next = item.role === "TEACHER" ? "ADMIN" : "TEACHER"; const consequence = next === "ADMIN" ? "активные назначения будут архивированы" : "архивные назначения не восстановятся"; act(() => employeesApi.changeRole(item.profile_id, next), `Изменить роль ${item.role} → ${next}? Все сеансы будут завершены; ${consequence}.`); }}>Изменить роль</Button>}</div></li>;
}
export default function AccessAccountsPage() { return <AuthGate route="dashboard"><Content /></AuthGate>; }
function Content() {
  const { current } = useAuth();
  const director = current?.user.role === "DIRECTOR";
  const [data, setData] = useState<AccessSections | null>(null); const [selected, setSelected] = useState<string[]>([]); const [preview, setPreview] = useState<BulkResponse | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function load() { setError(""); try { setData(await accountAccessApi.list()); } catch (reason) { setError(userMessage(reason)); } }
  useEffect(() => { void Promise.resolve().then(load); }, []);
  async function bulk(confirm: boolean) { setBusy(true); setError(""); try { const result = await accountAccessApi.bulkParents(selected, confirm); setPreview(result); if (confirm) { setSelected([]); await load(); } } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); } }
  async function act(operation: () => Promise<unknown>, confirmation?: string) { if (confirmation && !window.confirm(confirmation)) return; setBusy(true); setError(""); try { await operation(); await load(); } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); } }
  return <AppShell><div className="page-heading"><span className="eyebrow">Контроль доступа</span><h1>Доступ и аккаунты</h1><p>Приглашения и управление доступом без передачи временных паролей.</p></div>{error && <Alert>{error}</Alert>}{!data ? <Loading /> : <>
    <section className="section-space"><h2>Массовые приглашения родителей</h2><p>Выберите до 100 родителей, затем проверьте предварительный расчёт. Повторная отправка доступна только для неудачных или истёкших приглашений.</p><div className="action-row"><Button disabled={busy || selected.length === 0} onClick={() => void bulk(false)}>Предварительный просмотр ({selected.length})</Button>{preview && <Button disabled={busy || preview.preflight.eligible === 0} onClick={() => { if (window.confirm(`Отправить приглашения: ${preview.preflight.eligible}?`)) void bulk(true); }}>Подтвердить отправку</Button>}</div>{preview && <Alert tone="success">Доступно к отправке: {preview.preflight.eligible}; без/с неверным email: {preview.preflight.missing_or_invalid_email}; активированы: {preview.preflight.activated}; уже приглашены: {preview.preflight.already_invited}; ошибка или срок истёк (доступны для повтора): {preview.preflight.failed_or_expired}; заблокированы: {preview.preflight.blocked}; архивные: {preview.preflight.archived}; без активного связанного ребёнка: {preview.preflight.no_active_linked_child}.</Alert>}</section>
    {sections.map(([key, title]) => <section key={key} className="section-space"><h2>{title}</h2>{data[key].length ? <ul className="record-list">{data[key].map((item) => <Row key={`${item.profile_type}-${item.profile_id}`} item={item} selected={selected.includes(item.profile_id)} director={director} busy={busy} act={(operation, confirmation) => void act(operation, confirmation)} toggle={key === "parents" ? () => setSelected((current) => current.includes(item.profile_id) ? current.filter((id) => id !== item.profile_id) : current.length < 100 ? [...current, item.profile_id] : current) : undefined} />)}</ul> : <p className="empty-state">Нет записей.</p>}</section>)}
  </>}</AppShell>;
}
