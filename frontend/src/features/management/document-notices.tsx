"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { DocumentNotice, TeacherProjection } from "@/types/management";
import { fullName, ManagerPage } from "./common";

export function DocumentNoticesPage() {
  return <ManagerPage><DocumentNoticesContent /></ManagerPage>;
}

function DocumentNoticesContent() {
  const [teachers, setTeachers] = useState<TeacherProjection[]>([]);
  const [items, setItems] = useState<DocumentNotice[]>([]);
  const [recipient, setRecipient] = useState("");
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("policy_update");
  const [requiresAck, setRequiresAck] = useState(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [teacherList, notices] = await Promise.all([
        managementApi.teachers({ status: "active", account_status: "active" }),
        managementApi.documentNotices(),
      ]);
      setTeachers(teacherList.items);
      setItems(notices.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    const teacher = teachers.find((item) => item.employee_id === recipient);
    if (!teacher?.account) return;
    setBusy(true); setError("");
    try {
      await managementApi.createDocumentNotice({
        recipient_user_id: teacher.account.user_id,
        title: title.trim(),
        kind: kind.trim(),
        requires_ack: requiresAck,
      });
      setTitle("");
      await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Документы</span><h1>Уведомления о документах</h1><p>Метаданные и подтверждение ознакомления — без файлов, PDF и сканов.</p></div>
    {error && <Alert>{error}</Alert>}
    <form className="card section-card" onSubmit={(event) => void create(event)}>
      <div className="form-grid">
        <label>Воспитатель <select required className="input" value={recipient} onChange={(event) => setRecipient(event.target.value)}><option value="">Выберите</option>{teachers.map((item) => <option key={item.employee_id} value={item.employee_id}>{fullName(item)}</option>)}</select></label>
        <label>Название <Input required maxLength={240} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
        <label>Тип <Input required maxLength={64} value={kind} onChange={(event) => setKind(event.target.value)} /></label>
        <label><input type="checkbox" checked={requiresAck} onChange={(event) => setRequiresAck(event.target.checked)} /> Требуется подтверждение</label>
      </div>
      <Button disabled={busy}>{busy ? "Отправка..." : "Выдать уведомление"}</Button>
    </form>
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">Уведомлений о документах нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="record-link">
      <strong>{item.title}</strong>
      <span className="muted">{item.kind} · {item.requires_ack ? (item.acknowledged_at ? "подтверждено" : "ожидает подтверждения") : "без подтверждения"}</span>
    </div></li>)}</ul>}
  </>;
}
