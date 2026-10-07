"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { accountAccessApi, type AccessItem, type AccessSections, type BulkResponse } from "@/lib/api/account-access";
import { userMessage } from "@/lib/api/client";

const labels = { no_account: "Нет аккаунта", invited: "Приглашение отправлено", delivery_failed: "Ошибка отправки", invite_expired: "Срок приглашения истёк", activated: "Активирован", blocked: "Заблокирован" } as const;
const sections: Array<[keyof AccessSections, string]> = [["parents", "Родители"], ["teachers", "Воспитатели"], ["administrators", "Администраторы"], ["other_employees", "Прочие сотрудники"], ["blocked", "Заблокированные"]];

function Row({ item, selected, toggle }: { item: AccessItem; selected: boolean; toggle?: () => void }) {
  return <li className="card section-card">{toggle && <label><input type="checkbox" checked={selected} onChange={toggle} /> Выбрать</label>}<h3>{item.full_name}</h3><p>{item.context}{item.groups.length ? ` · ${item.groups.join(", ")}` : ""}</p><p>Статус: <strong>{labels[item.status]}</strong></p><p>Логин: {item.username || "—"} · Email: {item.masked_email || "—"}</p>{item.last_login_at && <p className="muted">Последний вход: {new Date(item.last_login_at).toLocaleString("ru-RU")}</p>}</li>;
}
export default function AccessAccountsPage() { return <AuthGate route="dashboard"><Content /></AuthGate>; }
function Content() {
  const [data, setData] = useState<AccessSections | null>(null); const [selected, setSelected] = useState<string[]>([]); const [preview, setPreview] = useState<BulkResponse | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function load() { setError(""); try { setData(await accountAccessApi.list()); } catch (reason) { setError(userMessage(reason)); } }
  useEffect(() => { void Promise.resolve().then(load); }, []);
  async function bulk(confirm: boolean) { setBusy(true); setError(""); try { const result = await accountAccessApi.bulkParents(selected, confirm); setPreview(result); if (confirm) { setSelected([]); await load(); } } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); } }
  return <AppShell><div className="page-heading"><span className="eyebrow">Контроль доступа</span><h1>Доступ и аккаунты</h1><p>Приглашения и управление доступом без передачи временных паролей.</p></div>{error && <Alert>{error}</Alert>}{!data ? <Loading /> : <>
    <section className="section-space"><h2>Массовые приглашения родителей</h2><p>Выберите до 100 родителей, затем проверьте предварительный расчёт.</p><div className="action-row"><Button disabled={busy || selected.length === 0} onClick={() => void bulk(false)}>Предварительный просмотр ({selected.length})</Button>{preview && <Button disabled={busy || preview.preflight.eligible === 0} onClick={() => { if (window.confirm(`Отправить приглашения: ${preview.preflight.eligible}?`)) void bulk(true); }}>Подтвердить отправку</Button>}</div>{preview && <Alert tone="success">Доступно: {preview.preflight.eligible}; без email: {preview.preflight.missing_or_invalid_email}; уже приглашены: {preview.preflight.already_invited}; активированы: {preview.preflight.activated}; заблокированы: {preview.preflight.blocked}.</Alert>}</section>
    {sections.map(([key, title]) => <section key={key} className="section-space"><h2>{title}</h2>{data[key].length ? <ul className="record-list">{data[key].map((item) => <Row key={`${item.profile_type}-${item.profile_id}`} item={item} selected={selected.includes(item.profile_id)} toggle={key === "parents" ? () => setSelected((current) => current.includes(item.profile_id) ? current.filter((id) => id !== item.profile_id) : current.length < 100 ? [...current, item.profile_id] : current) : undefined} />)}</ul> : <p className="empty-state">Нет записей.</p>}</section>)}
  </>}</AppShell>;
}
