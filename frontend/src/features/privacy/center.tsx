"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { userMessage } from "@/lib/api/client";
import { privacyApi, type PaperConsent, type PrivacyOverview, type PrivacyRequest, type Purpose, type RequestKind, type RequestStatus, type Subject } from "@/lib/api/privacy";
import { Documents } from "./documents";

const kinds: Record<RequestKind, string> = { access: "Сведения о своих данных", correction: "Исправление данных", withdrawal: "Отзыв согласия", stop_processing: "Прекращение обработки", erasure: "Удаление при наличии законных оснований" };
const statuses: Record<RequestStatus, string> = { submitted: "Зарегистрировано", verifying: "Проверка полномочий", in_review: "На рассмотрении", completed: "Исполнено вне системы", declined: "Мотивированный отказ" };
const roleNames: Record<string, string> = { DIRECTOR: "Директор", ADMIN: "Администратор", TEACHER: "Воспитатель", PARENT: "Родитель" };
const date = (value: string) => new Date(value).toLocaleString("ru-RU");
const subjectKey = (s: Subject) => [s.subject_user_id, s.child_id, s.guardian_id].join(":");

export function PrivacyCenter() {
  const { current } = useAuth();
  const [data, setData] = useState<PrivacyOverview | null>(null);
  const [consents, setConsents] = useState<PaperConsent[]>([]);
  const [requests, setRequests] = useState<PrivacyRequest[]>([]);
  const [queue, setQueue] = useState<PrivacyRequest[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const director = current?.user.role === "DIRECTOR";
  const manager = director || current?.user.role === "ADMIN";
  const load = useCallback(async () => {
    try {
      const [overview, evidence, cases, choices, operatorCases] = await Promise.all([
        privacyApi.me(), privacyApi.consents(), privacyApi.requests(), privacyApi.subjects(), director ? privacyApi.requests(true) : Promise.resolve([]),
      ]);
      setData(overview); setConsents(evidence); setRequests(cases); setSubjects(choices); setQueue(operatorCases); setError("");
    } catch (reason) { setError(userMessage(reason)); }
  }, [director]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function withdraw(id: string) {
    if (busy || !window.confirm("Зарегистрировать отзыв этого согласия? Он не удаляет данные по другим самостоятельным основаниям.")) return;
    setBusy(true); setError("");
    try { await privacyApi.withdraw(id); await load(); } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  }
  const content = <>
    <h1>Конфиденциальность</h1><Alert>Подготовительный режим: только синтетические данные. Работа с реальными персональными данными требует отдельной юридической и эксплуатационной приёмки.</Alert>
    {error && <Alert>{error}<Button variant="secondary" onClick={() => void load()}>Повторить загрузку</Button></Alert>}
    {!data ? <p>Загрузка…</p> : <>
      <section className="section-space"><h2>Оператор и документы</h2><p>Организация: {data.organization_name}. {data.operator_configured ? "Реквизиты оператора приведены в опубликованном документе." : "Юридические реквизиты оператора ещё не подтверждены."}</p>
        <p>Поставщик ПРОМАКС и оператор организации описываются отдельно. Подтверждение сотрудника не является согласием другого человека.</p>
        <Link className="text-link" href={`/privacy?garden=${encodeURIComponent(data.organization_id)}`}>Публичная страница документов организации</Link>
        <Documents documents={data.documents} />
      </section>
      <section className="section-space"><h2>Реестр целей обработки</h2>{!data.purposes.length && <p>Реестр ещё не заполнен. Основания и сроки не утверждены.</p>}{data.purposes.map(p => <details className="card section-card" key={p.id}>
        <summary>{p.title} · версия {p.version} · {p.ready ? "Настроено по утверждённому документу" : "Не утверждено или не действует"}</summary>
        <p>Оператор: {data.organization_name} — см. юридические реквизиты документа.</p><p>Субъекты: {p.subject_categories.map(s => s === "child" ? "дети" : "пользователи").join(", ")}</p><p>Категории данных: {p.data_categories.join(", ")}</p>
        <p>Основание: {p.legal_basis || "Не утверждено"}</p><p>Операции: {p.operations.join(", ")}</p><p>Доступ: {p.access_roles.map(r => roleNames[r]).join(", ")}</p><p>Хранение: {p.retention || "Не утверждено"}</p>
        <p>Подрядчики: {p.processors === null ? "Не подтверждены" : p.processors.join(", ") || "Подтверждено отсутствие"}</p><p>Места обработки: {p.locations?.join(", ") || "Не подтверждены"}</p><p>Необходимость согласия: {p.consent_required === null ? "Не определена" : p.consent_required ? "Требуется отдельное согласие" : "Основание не является согласием"}</p>
      </details>)}</section>
      <section className="section-space"><h2>{manager ? "Учёт бумажных согласий" : "Мои согласия"}</h2>
        <p>Здесь учитываются сведения о бумажном оригинале. Это не подписание согласия в ПРОМАКС. Оригинал остаётся в организации; сканы, паспорта и подписи не загружаются.</p>
        {manager && <PaperForm purposes={data.purposes} subjects={subjects} saved={load} />}
        {!consents.length && <p>Применимых записей нет. Вход в кабинет не создаёт согласий.</p>}
        {consents.map(c => <article className="card section-card section-space" key={c.id}>
          <h3>{c.purpose_title}</h3><p>{subjects.find(s => subjectKey(s) === subjectKey({ ...c, label: "" }))?.label || "Субъект в пределах разрешённого доступа"}</p>
          <p>Бумажное согласие · версия {c.document_version} · получено {c.received_on}</p><p>Статус: {c.status === "withdrawn" ? "Отозвано" : "Сведения об оригинале учтены"}. {!c.current_version && "Версия больше не применяется; новое согласие автоматически не создаётся."}</p>
          <p>Ответственный за учёт: {c.recorded_by === current?.user.id ? "Вы" : subjects.find(s => s.subject_user_id === c.recorded_by)?.label || "Уполномоченный сотрудник организации"}.</p>
          <details><summary>История и версия</summary><p style={{ overflowWrap: "anywhere" }}>SHA-256: {c.document_hash}</p>{c.document && <Documents documents={[c.document]} />}{c.history.map((e, i) => <p key={i}>{e.action === "recorded" ? "Оригинал учтён уполномоченным сотрудником" : "Отзыв зарегистрирован"} · {date(e.at)}</p>)}</details>
          {c.status !== "withdrawn" && <Button variant="secondary" disabled={busy} onClick={() => void withdraw(c.id)}>Отозвать согласие</Button>}
        </article>)}
      </section>
      <section className="section-space"><h2>Обращения к оператору</h2><p>Обращение поступает директору вашей организации. Полномочия и законные основания проверяются отдельно. Исправление, предоставление сведений и удаление выполняются после проверки вне этого журнала.</p>
        <p>Не отправляйте паспортные или медицинские сведения. Дополнительные сведения передаются только через подтверждённый канал оператора, указанный в документе.</p>
        <RequestForm subjects={current?.user.role === "PARENT" ? subjects : []} saved={load} />
        <h3>Мои обращения</h3>{!requests.length && <p>Обращений пока нет.</p>}{requests.map(item => <RequestCard key={item.id} item={item} />)}
      </section>
      {director && <section className="section-space"><h2>Журнал обращений оператору</h2><p>Установите срок после правовой классификации обращения. Срок не рассчитывается автоматически. Завершение статуса не выполняет удаление или выдачу данных.</p>
        {!queue.length && <p>Обращений нет.</p>}{queue.map(item => <RequestCard key={item.id} item={item}><RequestControls item={item} saved={load} /></RequestCard>)}
      </section>}
    </>}
  </>;
  return current?.user.role === "PARENT" ? <main className="main-content" style={{ maxWidth: 1000, margin: "auto" }}><Link className="text-link" href="/parent">В кабинет родителя</Link>{content}</main> : <AppShell>{content}</AppShell>;
}

function PaperForm({ purposes, subjects, saved }: { purposes: Purpose[]; subjects: Subject[]; saved: () => Promise<void> }) {
  const eligible = purposes.filter(p => p.ready && p.consent_required && p.consent_document_id);
  const [purposeId, setPurposeId] = useState(""); const [subjectId, setSubjectId] = useState(""); const [receivedOn, setReceivedOn] = useState("");
  const [original, setOriginal] = useState(false); const [authority, setAuthority] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const key = useRef<string | null>(null);
  const purpose = eligible.find(p => p.id === purposeId);
  const choices = subjects.filter(s => purpose?.subject_categories.includes(s.child_id ? "child" : "user"));
  async function submit(e: React.FormEvent) {
    e.preventDefault(); const subject = choices.find(s => subjectKey(s) === subjectId);
    if (busy || !purpose?.consent_document_id || !subject || !original || !authority) return;
    setBusy(true); setError(""); key.current ??= crypto.randomUUID();
    try { await privacyApi.record({ purpose_id: purpose.id, document_id: purpose.consent_document_id, subject_user_id: subject.subject_user_id, child_id: subject.child_id, guardian_id: subject.guardian_id, received_on: receivedOn, idempotency_key: key.current }); key.current = null; setOriginal(false); setAuthority(false); await saved(); }
    catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  }
  if (!eligible.length) return <p>Нет действующих утверждённых целей, требующих согласия. Учёт для неподтверждённых или отложенных целей недоступен.</p>;
  return <form className="card section-card" onSubmit={e => void submit(e)} onChange={() => { key.current = null; }}><h3>Учесть бумажный оригинал</h3>
    <label>Цель согласия<select className="input" value={purposeId} onChange={e => { setPurposeId(e.target.value); setSubjectId(""); }} required><option value="">Выберите цель</option>{eligible.map(p => <option key={p.id} value={p.id}>{p.title} · {p.version}</option>)}</select></label>
    <label>Субъект и представитель<select className="input" required value={subjectId} onChange={e => setSubjectId(e.target.value)}><option value="">Выберите</option>{choices.map(s => <option key={subjectKey(s)} value={subjectKey(s)}>{s.label}</option>)}</select></label>
    <label>Дата получения оригинала<input className="input" type="date" required value={receivedOn} onChange={e => setReceivedOn(e.target.value)} /></label>
    <label><input type="checkbox" checked={original} onChange={e => setOriginal(e.target.checked)} /> Бумажный оригинал получен и хранится в организации.</label><br />
    <label><input type="checkbox" checked={authority} onChange={e => setAuthority(e.target.checked)} /> Я проверил полномочия подписанта и соответствие оригинала выбранной версии.</label>
    {error && <Alert>{error}</Alert>}<Button disabled={busy || !purposeId || !subjectId || !receivedOn || !original || !authority}>Учесть оригинал</Button>
  </form>;
}

function RequestForm({ subjects, saved }: { subjects: Subject[]; saved: () => Promise<void> }) {
  const [kind, setKind] = useState<RequestKind>("access"); const [child, setChild] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const key = useRef<string | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (busy) return; setBusy(true); setError(""); key.current ??= crypto.randomUUID();
    try { await privacyApi.request(kind, child || null, key.current); key.current = null; await saved(); } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  }
  return <form className="card section-card" onSubmit={e => void submit(e)} onChange={() => { key.current = null; }}>
    <label>Тип обращения<select className="input" value={kind} onChange={e => setKind(e.target.value as RequestKind)}>{Object.entries(kinds).map(([k, label]) => <option key={k} value={k}>{label}</option>)}</select></label>
    <label>Относительно<select className="input" value={child} onChange={e => setChild(e.target.value)}><option value="">Моих данных</option>{subjects.filter(s => s.child_id).map(s => <option key={s.child_id} value={s.child_id!}>{s.label}</option>)}</select></label>
    {error && <Alert>{error}</Alert>}<Button disabled={busy}>{busy ? "Отправка…" : "Зарегистрировать обращение"}</Button>
  </form>;
}

function RequestCard({ item, children }: { item: PrivacyRequest; children?: React.ReactNode }) {
  return <article className="card section-card section-space"><h3>{kinds[item.kind]}</h3><p>Обращение {item.id.slice(0, 8)} · {date(item.created_at)} · {statuses[item.status]}</p>
    <p>{item.needs_deadline ? "Оператору необходимо определить срок ответа." : item.due_at ? `Срок: ${date(item.due_at)}` : ""}{item.overdue && " Срок истёк — требуется внимание оператора."}</p>
    <details><summary>История статусов</summary>{item.history.map((e, i) => <p key={i}>{date(e.at)} · {statuses[e.status]}{e.decision_code && ` · ${({ fulfilled_offline: "Исполнено по проверенному каналу", independent_legal_basis: "Имеется самостоятельное основание", authority_not_verified: "Полномочия не подтверждены", not_applicable: "Не применимо" } as Record<string, string>)[e.decision_code]}`}</p>)}</details>{children}
  </article>;
}

function RequestControls({ item, saved }: { item: PrivacyRequest; saved: () => Promise<void> }) {
  const [due, setDue] = useState(""); const [reason, setReason] = useState("independent_legal_basis"); const [confirmed, setConfirmed] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function move(status: RequestStatus) {
    if (busy) return; setBusy(true); setError("");
    try { await privacyApi.transition(item.id, { status, expected_status: item.status, ...(due ? { due_at: new Date(due).toISOString() } : {}), ...(["completed", "declined"].includes(status) ? { outcome_confirmed: confirmed, decision_code: status === "completed" ? "fulfilled_offline" : reason } : {}) }); setConfirmed(false); await saved(); }
    catch (error) { setError(userMessage(error)); } finally { setBusy(false); }
  }
  if (item.status === "completed" || item.status === "declined") return null;
  return <div className="section-space"><label>Проверенный срок ответа (местное время браузера)<input className="input" type="datetime-local" value={due} onChange={e => setDue(e.target.value)} /></label>
    {item.status === "submitted" ? <Button disabled={busy || (!due && !item.due_at)} onClick={() => void move("verifying")}>Начать проверку полномочий</Button> : <>
      {item.status === "verifying" && <Button disabled={busy || (!due && !item.due_at)} onClick={() => void move("in_review")}>Передать на рассмотрение</Button>}
      <label>Основание отказа<select className="input" value={reason} onChange={e => setReason(e.target.value)}><option value="independent_legal_basis">Самостоятельное законное основание</option><option value="authority_not_verified">Полномочия не подтверждены</option><option value="not_applicable">Требование не применимо</option></select></label>
      <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /> Решение проверено, ответ направлен по подтверждённому каналу.</label>
      <div className="action-row">{item.status === "in_review" && <Button disabled={busy || !confirmed} onClick={() => void move("completed")}>Зафиксировать исполнение</Button>}<Button variant="secondary" disabled={busy || !confirmed} onClick={() => void move("declined")}>Зафиксировать мотивированный отказ</Button></div>
    </>}{error && <Alert>{error}</Alert>}
  </div>;
}
