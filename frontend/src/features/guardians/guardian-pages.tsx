"use client";

/**
 * Guardian screens collect only Stage 2 contact fields and use tenant-scoped API calls.
 * Names, phone and email are never persisted in browser storage or URL search.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { guardiansApi } from "@/lib/api/guardians";
import { childrenApi } from "@/lib/api/children";
import { GuardianRelations } from "@/features/guardians/relation-controls";
import { ApiError, userMessage } from "@/lib/api/client";
import { RELATION_LABELS, type Guardian, type GuardianFields, type GuardianListItem, type RelationType, type StatusFilter } from "@/types/stage2";

function fullName(item: { last_name: string; first_name: string; middle_name: string | null }) {
  return [item.last_name, item.first_name, item.middle_name].filter(Boolean).join(" ");
}

const emptyFields: GuardianFields = { last_name: "", first_name: "", middle_name: null, phone: null, email: null };

function GuardianForm({ initial = emptyFields, busy, submit, cancel }: {
  initial?: GuardianFields;
  busy: boolean;
  submit: (fields: GuardianFields) => Promise<void>;
  cancel?: () => void;
}) {
  const [fields, setFields] = useState<GuardianFields>(initial);
  const submitting = useRef(false);
  function set<K extends keyof GuardianFields>(key: K, value: GuardianFields[K]) {
    setFields((previous) => ({ ...previous, [key]: value }));
  }
  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    try {
      await submit({
        last_name: fields.last_name.trim(),
        first_name: fields.first_name.trim(),
        middle_name: fields.middle_name?.trim() || null,
        phone: fields.phone?.trim() || null,
        email: fields.email?.trim() || null,
      });
    } finally { submitting.current = false; }
  }
  return <form className="card section-card" onSubmit={(event) => void onSubmit(event)}>
    <div className="form-grid">
      <FormField id="guardian-last-name" label="Фамилия"><Input id="guardian-last-name" required maxLength={100} value={fields.last_name} onChange={(event) => set("last_name", event.target.value)} /></FormField>
      <FormField id="guardian-first-name" label="Имя"><Input id="guardian-first-name" required maxLength={100} value={fields.first_name} onChange={(event) => set("first_name", event.target.value)} /></FormField>
      <FormField id="guardian-middle-name" label="Отчество (необязательно)"><Input id="guardian-middle-name" maxLength={100} value={fields.middle_name ?? ""} onChange={(event) => set("middle_name", event.target.value)} /></FormField>
      <FormField id="guardian-phone" label="Телефон (необязательно)"><Input id="guardian-phone" type="tel" maxLength={32} value={fields.phone ?? ""} onChange={(event) => set("phone", event.target.value)} /></FormField>
      <FormField id="guardian-email" label="Email (необязательно)"><Input id="guardian-email" type="email" maxLength={254} value={fields.email ?? ""} onChange={(event) => set("email", event.target.value)} /></FormField>
    </div>
    <div className="action-row"><Button type="submit" disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</Button>{cancel && <Button type="button" variant="secondary" onClick={cancel}>Отмена</Button>}</div>
  </form>;
}

export function GuardiansPage() {
  return <AuthGate route="dashboard"><GuardiansContent /></AuthGate>;
}

function GuardiansContent() {
  const [items, setItems] = useState<GuardianListItem[]>([]);
  const [status, setStatus] = useState<StatusFilter>("active");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setItems((await guardiansApi.list({ status })).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [status]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const visible = items.filter((guardian) => fullName(guardian).toLocaleLowerCase("ru").includes(search.trim().toLocaleLowerCase("ru")));
  return <AppShell><div className="page-heading"><span className="eyebrow">Управление</span><h1>Родители и законные представители</h1><p>Контакты только в объёме, нужном для работы сада.</p><Link className="button button-primary" href="/guardians/new">Добавить представителя</Link></div>
    <div className="filter-row"><label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}><option value="active">Активные</option><option value="archived">Архив</option><option value="all">Все</option></select></label>
      <label>Поиск по имени <Input value={search} onChange={(event) => setSearch(event.target.value)} /></label></div>
    {error && <Alert>{error}</Alert>}{loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button> : visible.length === 0 ? <p className="empty-state">Представители не найдены.</p> : <ul className="record-list">{visible.map((guardian) => <li key={guardian.id}><Link href={`/guardians/${guardian.id}`} className="record-link"><strong>{fullName(guardian)}</strong><span className="muted">{guardian.phone ?? guardian.email ?? "Контакты не указаны"} · {guardian.account ? `Аккаунт: ${guardian.account.status === "active" ? "активен" : "заблокирован"}` : "Без аккаунта"} · {guardian.status === "active" ? "Активен" : "Архив"}</span></Link></li>)}</ul>}
  </AppShell>;
}

export function NewGuardianPage({ childId }: { childId?: string }) {
  return <AuthGate route="dashboard"><NewGuardianContent childId={childId} /></AuthGate>;
}

function NewGuardianContent({ childId }: { childId?: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [relationType, setRelationType] = useState<RelationType>("other");
  const createdId = useRef<string | null>(null);
  async function create(fields: GuardianFields) {
    setBusy(true); setError("");
    try {
      if (!createdId.current) createdId.current = (await guardiansApi.create(fields)).id;
      if (childId) await childrenApi.link(childId, createdId.current, relationType);
      router.push(childId ? `/children/${childId}` : `/guardians/${createdId.current}`);
    }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <AppShell><Link className="text-link" href={childId ? `/children/${childId}` : "/guardians"}>← Назад</Link><div className="page-heading section-space"><h1>Добавить представителя</h1></div>{error && <Alert>{error}</Alert>}
    {childId && <div className="field"><label htmlFor="new-guardian-relation">Отношение к ребёнку</label><select className="input" id="new-guardian-relation" value={relationType} onChange={(event) => setRelationType(event.target.value as RelationType)}>{Object.entries(RELATION_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>}
    <GuardianForm busy={busy} submit={create} />
  </AppShell>;
}

export function GuardianDetailPage({ id }: { id: string }) {
  return <AuthGate route="dashboard"><GuardianDetail id={id} /></AuthGate>;
}

function GuardianDetail({ id }: { id: string }) {
  const [guardian, setGuardian] = useState<Guardian | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setGuardian(await guardiansApi.get(id)); }
    catch (reason) { setError(reason instanceof ApiError && reason.status === 404 ? "Запись не найдена." : userMessage(reason)); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function save(fields: GuardianFields) {
    setBusy(true); setError(""); setMessage("");
    try { setGuardian(await guardiansApi.update(id, fields)); setEditing(false); setMessage("Карточка сохранена."); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  async function changeStatus() {
    if (!guardian || busy) return;
    if (guardian.status === "active" && !window.confirm("Архивировать представителя? Связанный аккаунт родителя будет заблокирован.")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      setGuardian(guardian.status === "active" ? await guardiansApi.archive(id) : await guardiansApi.restore(id));
      setMessage(guardian.status === "active" ? "Карточка архивирована." : "Карточка восстановлена. Аккаунт родителя нужно разблокировать отдельно.");
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <AppShell><Link className="text-link" href="/guardians">← К списку представителей</Link>
    {loading ? <div className="section-space"><Loading /></div> : error && !guardian ? <div className="section-space"><Alert>{error}</Alert><Button variant="secondary" onClick={() => void load()}>Повторить</Button></div> : guardian && <>
      <div className="page-heading section-space"><span className="eyebrow">Представитель · {guardian.status === "active" ? "Активен" : "Архив"}</span><h1>{fullName(guardian)}</h1></div>
      {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
      {editing ? <GuardianForm key={guardian.updated_at} initial={{ first_name: guardian.first_name, last_name: guardian.last_name, middle_name: guardian.middle_name, phone: guardian.phone, email: guardian.email }} busy={busy} submit={save} cancel={() => setEditing(false)} /> : <section className="card section-card">
        <p>Телефон: {guardian.phone ?? "Не указан"}</p><p>Email: {guardian.email ?? "Не указан"}</p>
        <div className="action-row"><Button variant="secondary" onClick={() => setEditing(true)}>Изменить</Button><Button variant="secondary" disabled={busy} onClick={() => void changeStatus()}>{guardian.status === "active" ? "Архивировать" : "Восстановить"}</Button></div>
      </section>}
      <GuardianRelations guardian={guardian} refresh={load} />
      <section className="section-space"><h2>Учётная запись родителя</h2><p className="card section-card">{guardian.account ? `${guardian.account.username} · ${guardian.account.status === "active" ? "Активна" : "Заблокирована"}` : "Не создана."}</p></section>
    </>}
  </AppShell>;
}
