"use client";

/** Employee screens: editable values and one-time credentials stay in component memory only. */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { useAuth } from "@/features/auth/auth-provider";
import { employeesApi } from "@/lib/api/employees";
import { userMessage } from "@/lib/api/client";
import type { Employee, EmployeeFields, EmployeeSummary, TemporaryCredentials } from "@/types/stage3";

const empty: EmployeeFields = { first_name: "", last_name: "", middle_name: null, position: "" };
const name = (e: EmployeeSummary) => [e.last_name, e.first_name, e.middle_name].filter(Boolean).join(" ");

function Form({ initial = empty, busy, submit, cancel }: { initial?: EmployeeFields; busy: boolean; submit: (fields: EmployeeFields) => Promise<void>; cancel?: () => void }) {
  const [fields, setFields] = useState(initial);
  const submitting = useRef(false);
  function set(key: keyof EmployeeFields, value: string) { setFields((old) => ({ ...old, [key]: value })); }
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (submitting.current) return;
    submitting.current = true;
    try { await submit({ first_name: fields.first_name.trim(), last_name: fields.last_name.trim(), middle_name: fields.middle_name?.trim() || null, position: fields.position.trim() }); }
    finally { submitting.current = false; }
  }
  return <form className="card section-card" onSubmit={(event) => void save(event)}><div className="form-grid">
    {([["last_name", "Фамилия"], ["first_name", "Имя"], ["middle_name", "Отчество (необязательно)"], ["position", "Должность"]] as const).map(([key, label]) => <label key={key}>{label}<Input required={key !== "middle_name"} maxLength={100} value={fields[key] ?? ""} onChange={(event) => set(key, event.target.value)} /></label>)}
  </div><div className="action-row"><Button disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</Button>{cancel && <Button type="button" variant="secondary" onClick={cancel}>Отмена</Button>}</div></form>;
}

export function EmployeesPage() { return <AuthGate route="dashboard"><EmployeesContent /></AuthGate>; }
function EmployeesContent() {
  const [items, setItems] = useState<EmployeeSummary[]>([]);
  const [status, setStatus] = useState<"active" | "archived" | "all">("active");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setItems((await employeesApi.list(status)).items); } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [status]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const visible = items.filter((item) => name(item).toLocaleLowerCase("ru").includes(search.trim().toLocaleLowerCase("ru")));
  return <AppShell><div className="page-heading"><span className="eyebrow">Управление</span><h1>Сотрудники</h1><p>Карточки сотрудников вашего сада.</p><Link className="button button-primary" href="/employees/new">Добавить сотрудника</Link></div>
    <div className="filter-row"><label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="active">Активные</option><option value="archived">Архив</option><option value="all">Все</option></select></label><label>Поиск по имени <Input value={search} onChange={(event) => setSearch(event.target.value)} /></label></div>
    {error && <Alert>{error}</Alert>}{loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : visible.length === 0 ? <p className="empty-state">Сотрудники не найдены.</p> : <ul className="record-list">{visible.map((item) => <li key={item.id}><Link className="record-link" href={`/employees/${item.id}`}><strong>{name(item)}</strong><span className="muted">{item.position} · {item.status === "active" ? "Активен" : "Архив"} · {item.account ? "Доступ ADMIN" : "Без доступа"}</span></Link></li>)}</ul>}
  </AppShell>;
}

export function NewEmployeePage() { return <AuthGate route="dashboard"><NewContent /></AuthGate>; }
function NewContent() {
  const router = useRouter(); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function save(fields: EmployeeFields) { setBusy(true); setError(""); try { const item = await employeesApi.create(fields); router.push(`/employees/${item.id}`); } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); } }
  return <AppShell><Link className="text-link" href="/employees">← К сотрудникам</Link><div className="page-heading section-space"><h1>Добавить сотрудника</h1></div>{error && <Alert>{error}</Alert>}<Form busy={busy} submit={save} /></AppShell>;
}

export function EmployeeDetailPage({ id }: { id: string }) { return <AuthGate route="dashboard"><Detail id={id} /></AuthGate>; }
function Detail({ id }: { id: string }) {
  const { current } = useAuth(); const director = current?.user.role === "DIRECTOR";
  const [item, setItem] = useState<Employee | null>(null); const [credentials, setCredentials] = useState<TemporaryCredentials | null>(null);
  const [editing, setEditing] = useState(false); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const load = useCallback(async () => { setLoading(true); setError(""); try { setItem(await employeesApi.get(id)); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }, [id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function change(operation: () => Promise<Employee>, success: string): Promise<boolean> {
    setBusy(true); setError(""); setMessage("");
    try { setItem(await operation()); setMessage(success); return true; }
    catch (reason) { setError(userMessage(reason)); return false; }
    finally { setBusy(false); }
  }
  async function revealAccount(operation: () => Promise<TemporaryCredentials>, success: string) {
    setBusy(true); setError(""); setMessage(""); setCredentials(null);
    try {
      const result = await operation();
      // The POST response is the sole source of the one-time password. No follow-up GET can recover it.
      setItem((current) => current && { ...current, account: result.account });
      setCredentials(result);
      setMessage(success);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  async function updateAccount(operation: () => Promise<NonNullable<Employee["account"]>>, success: string) {
    setBusy(true); setError(""); setMessage(""); setCredentials(null);
    try { const result = await operation(); setItem((current) => current && { ...current, account: result }); setMessage(success); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <AppShell><Link className="text-link" href="/employees">← К сотрудникам</Link>{loading ? <Loading /> : !item ? <div className="section-space"><Alert>{error || "Запись не найдена."}</Alert><Button variant="secondary" onClick={() => void load()}>Повторить</Button></div> : <>
    <div className="page-heading section-space"><span className="eyebrow">Сотрудник · {item.status === "active" ? "Активен" : "Архив"}</span><h1>{name(item)}</h1><p>{item.position}</p></div>
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    {editing ? <Form initial={item} busy={busy} submit={async (fields) => { if (await change(() => employeesApi.update(id, fields), "Карточка сохранена.")) setEditing(false); }} cancel={() => setEditing(false)} /> : <div className="action-row"><Button variant="secondary" onClick={() => setEditing(true)}>Изменить</Button>{(director || !item.account) && <Button variant="secondary" disabled={busy} onClick={() => {
      if (item.status === "active" && !window.confirm(item.account ? "Архивировать сотрудника и заблокировать его доступ?" : "Архивировать сотрудника?")) return;
      void change(() => item.status === "active" ? employeesApi.archive(id) : employeesApi.restore(id), item.status === "active" ? "Карточка архивирована." : "Карточка восстановлена. Доступ остаётся заблокированным, если был выдан.");
    }}>{item.status === "active" ? "Архивировать" : "Восстановить"}</Button>}</div>}
    {item.account && <section className="card section-card section-space"><h2>Доступ администратора</h2><p>Логин: <strong>{item.account.username}</strong> · {item.account.status === "active" ? "Активен" : "Заблокирован"}{item.account.must_change_password ? " · Требуется смена пароля" : ""}</p>
      {director && <div className="action-row"><Button variant="secondary" disabled={busy} onClick={() => void revealAccount(() => employeesApi.resetPassword(id), "Временный пароль обновлён. Действующие сессии завершены.")}>Сбросить пароль</Button><Button variant="secondary" disabled={busy} onClick={() => void updateAccount(() => item.account?.status === "active" ? employeesApi.block(id) : employeesApi.unblock(id), item.account?.status === "active" ? "Доступ заблокирован." : "Доступ восстановлен.")}>{item.account.status === "active" ? "Заблокировать" : "Разблокировать"}</Button></div>}
    </section>}
    {director && !item.account && item.status === "active" && <div className="section-space"><Button disabled={busy} onClick={() => void revealAccount(() => employeesApi.createAccount(id), "Доступ выдан. Сохраните реквизиты сейчас.")}>Выдать доступ администратора</Button></div>}
    {credentials && <section className="card section-card section-space" aria-label="Одноразовые реквизиты"><h2>Временные реквизиты</h2><p>Логин: <strong>{credentials.account.username}</strong></p><p>Временный пароль: <strong>{credentials.temporary_password}</strong></p><p>Пароль появится только сейчас. Передайте его сотруднику безопасным способом.</p><Button variant="secondary" onClick={() => setCredentials(null)}>Закрыть и скрыть пароль</Button></section>}
  </>}</AppShell>;
}
