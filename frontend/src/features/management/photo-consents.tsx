"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { childrenApi } from "@/lib/api/children";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { ChildSummary } from "@/types/stage2";
import type { PhotoConsent } from "@/types/management";
import { fullName, ManagerPage, useQueryParam } from "./common";

export function PhotoConsentsPage() {
  return <ManagerPage><PhotoConsentsContent /></ManagerPage>;
}

function PhotoConsentsContent() {
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [items, setItems] = useState<PhotoConsent[]>([]);
  const [childId, setChildId] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useQueryParam("child_id", setChildId);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [childList, consents] = await Promise.all([
        childrenApi.list({ status: "active" }),
        managementApi.photoConsents(childId ? { child_id: childId } : {}),
      ]);
      setChildren(childList.items);
      setItems(consents.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [childId]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function record(event: React.FormEvent) {
    event.preventDefault();
    if (!childId || !effectiveFrom) return;
    setBusy(true); setError("");
    try {
      await managementApi.recordPhotoConsent({
        child_id: childId,
        effective_from: new Date(effectiveFrom).toISOString(),
      });
      await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Приватность</span><h1>Согласия на фото</h1><p>Техническое состояние согласия. Запись в системе сама по себе не подтверждает юридическую достаточность согласия.</p></div>
    {error && <Alert>{error}</Alert>}
    <form className="card section-card" onSubmit={(event) => void record(event)}>
      <div className="form-grid">
        <label>Ребёнок <select required className="input" value={childId} onChange={(event) => setChildId(event.target.value)}><option value="">Выберите</option>{children.map((child) => <option key={child.id} value={child.id}>{fullName(child)}</option>)}</select></label>
        <label>Действует с <Input required type="datetime-local" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} /></label>
      </div>
      <Button disabled={busy}>{busy ? "Сохранение..." : "Зафиксировать согласие"}</Button>
    </form>
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">Записей согласия нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="record-link">
      <strong>{item.status === "granted" ? "Согласие действует" : "Согласие отозвано"}</strong>
      <span className="muted">{new Date(item.effective_from).toLocaleString("ru-RU")}{item.effective_to ? " — " + new Date(item.effective_to).toLocaleString("ru-RU") : ""}</span>
      {item.status === "granted" && <Button variant="secondary" disabled={busy} onClick={() => {
        if (!window.confirm("Отозвать техническое состояние согласия?")) return;
        void managementApi.withdrawPhotoConsent(item.id).then(load).catch((reason) => setError(userMessage(reason)));
      }}>Отозвать</Button>}
    </div></li>)}</ul>}
  </>;
}
