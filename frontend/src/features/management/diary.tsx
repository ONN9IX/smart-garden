"use client";

import { useCallback, useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { childrenApi } from "@/lib/api/children";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { ChildSummary } from "@/types/stage2";
import type { DiaryEntry } from "@/types/management";
import { fullName, ManagerPage, SectionError, useQueryParam } from "./common";

export function DiaryPage() {
  return <ManagerPage><DiaryContent /></ManagerPage>;
}

function DiaryContent() {
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [childId, setChildId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [items, setItems] = useState<DiaryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useQueryParam("child_id", setChildId);

  useEffect(() => {
    void childrenApi.list({ status: "active" })
      .then((result) => setChildren(result.items))
      .catch((reason) => setError(userMessage(reason)));
  }, []);

  const load = useCallback(async () => {
    if (!childId) { setItems([]); return; }
    setLoading(true); setError("");
    try { setItems((await managementApi.diary(childId, dateFrom || undefined, dateTo || undefined)).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [childId, dateFrom, dateTo]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  return <>
    <div className="page-heading"><span className="eyebrow">Операционная информация</span><h1>Дневник ребёнка</h1><p>В управленческом кабинете дневник доступен только для чтения.</p></div>
    <div className="filter-row">
      <label>Ребёнок <select className="input" value={childId} onChange={(event) => setChildId(event.target.value)}><option value="">Выберите</option>{children.map((child) => <option key={child.id} value={child.id}>{fullName(child)}</option>)}</select></label>
      <label>С даты <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
      <label>По дату <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
    </div>
    <SectionError error={error} retry={() => void load()} />
    {loading ? <Loading /> : childId && items.length === 0 ? <p className="empty-state">Записей дневника нет.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="card section-card"><strong>{item.date}</strong><p>{item.note}</p></div></li>)}</ul>}
  </>;
}
