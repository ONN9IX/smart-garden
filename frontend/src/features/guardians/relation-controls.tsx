"use client";

/** Relation actions operate on tenant-bound UUIDs; server validates both entities and role. */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Loading } from "@/components/ui/loading";
import { childrenApi } from "@/lib/api/children";
import { guardiansApi } from "@/lib/api/guardians";
import { userMessage } from "@/lib/api/client";
import { RELATION_LABELS, type Child, type ChildSummary, type Guardian, type GuardianListItem, type RelationType } from "@/types/stage2";

function RelationSelect({ id, value, change, disabled }: { id: string; value: RelationType; change: (value: RelationType) => void; disabled?: boolean }) {
  return <select id={id} className="input compact-input" disabled={disabled} value={value} onChange={(event) => change(event.target.value as RelationType)}>
    {Object.entries(RELATION_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
  </select>;
}

export function ChildRelations({ child, refresh }: { child: Child; refresh: () => Promise<void> }) {
  const [guardians, setGuardians] = useState<GuardianListItem[]>([]);
  const [guardianId, setGuardianId] = useState("");
  const [relationType, setRelationType] = useState<RelationType>("other");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    try { setGuardians((await guardiansApi.list()).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function run(action: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true); setError("");
    try { await action(); await refresh(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  const existing = new Set(child.guardians.filter((relation) => relation.status === "active").map((relation) => relation.guardian.id));
  return <section className="section-space"><h2>Родители и законные представители</h2>
    {error && <Alert>{error}</Alert>}
    {child.guardians.length ? <ul className="record-list">{child.guardians.map((relation) => <li key={relation.id} className="card section-card">
      <div className="section-heading"><Link className="text-link" href={`/guardians/${relation.guardian.id}`}>{relation.guardian.last_name} {relation.guardian.first_name}</Link><span>{relation.status === "active" ? "Активная связь" : "Архив связи"}</span></div>
      <div className="action-row section-space"><label htmlFor={`relation-${relation.id}`}>Отношение</label><RelationSelect id={`relation-${relation.id}`} value={relation.relation_type} disabled={busy || relation.status !== "active"} change={(value) => void run(() => childrenApi.updateLink(child.id, relation.guardian.id, value))} />
        {relation.status === "active" ? <Button variant="secondary" disabled={busy} onClick={() => { if (window.confirm("Убрать связь с представителем?")) void run(() => childrenApi.archiveLink(child.id, relation.guardian.id)); }}>Убрать связь</Button>
          : <Button variant="secondary" disabled={busy} onClick={() => void run(() => childrenApi.restoreLink(child.id, relation.guardian.id))}>Восстановить связь</Button>}
      </div>
    </li>)}</ul> : <p className="empty-state">Представители пока не связаны с карточкой.</p>}
    {child.status === "active" && <div className="card section-card section-space"><h3>Добавить представителя</h3>
      {loading ? <Loading /> : <>
        <div className="filter-row"><label htmlFor="guardian-pick">Существующий представитель</label><select className="input" id="guardian-pick" value={guardianId} onChange={(event) => setGuardianId(event.target.value)}><option value="">Выберите представителя</option>{guardians.filter((guardian) => !existing.has(guardian.id)).map((guardian) => <option key={guardian.id} value={guardian.id}>{guardian.last_name} {guardian.first_name}</option>)}</select>
          <label htmlFor="relation-type">Отношение</label><RelationSelect id="relation-type" value={relationType} change={setRelationType} />
          <Button disabled={busy || !guardianId} onClick={() => void run(() => childrenApi.link(child.id, guardianId, relationType))}>Связать</Button></div>
        <Link className="text-link" href={`/guardians/new?child_id=${encodeURIComponent(child.id)}`}>Создать нового представителя и связать</Link>
      </>}
    </div>}
  </section>;
}

export function GuardianRelations({ guardian, refresh }: { guardian: Guardian; refresh: () => Promise<void> }) {
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [childId, setChildId] = useState("");
  const [relationType, setRelationType] = useState<RelationType>("other");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    try { setChildren((await childrenApi.list()).items); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  async function run(action: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true); setError("");
    try { await action(); await refresh(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  const linked = new Set(guardian.children.filter((relation) => relation.relation_status === "active").map((relation) => relation.child.id));
  return <section className="section-space"><h2>Дети</h2>{error && <Alert>{error}</Alert>}
    {guardian.children.length ? <ul className="record-list">{guardian.children.map((relation) => <li key={relation.relation_id} className="card section-card">
      <Link className="text-link" href={`/children/${relation.child.id}`}>{relation.child.last_name} {relation.child.first_name}</Link><p>{relation.child.group.name} · {relation.relation_status === "active" ? "Активная связь" : "Архив связи"}</p>
      <div className="action-row"><label htmlFor={`guardian-relation-${relation.relation_id}`}>Отношение</label><RelationSelect id={`guardian-relation-${relation.relation_id}`} value={relation.relation_type} disabled={busy || relation.relation_status !== "active"} change={(value) => void run(() => childrenApi.updateLink(relation.child.id, guardian.id, value))} />
        {relation.relation_status === "active" ? <Button variant="secondary" disabled={busy} onClick={() => { if (window.confirm("Убрать связь с ребёнком?")) void run(() => childrenApi.archiveLink(relation.child.id, guardian.id)); }}>Убрать связь</Button>
          : <Button variant="secondary" disabled={busy} onClick={() => void run(() => childrenApi.restoreLink(relation.child.id, guardian.id))}>Восстановить связь</Button>}
      </div>
    </li>)}</ul> : <p className="empty-state">Связанных детей пока нет.</p>}
    {guardian.status === "active" && <div className="card section-card section-space"><h3>Связать с ребёнком</h3>{loading ? <Loading /> : <div className="filter-row">
      <label htmlFor="child-pick">Ребёнок</label><select className="input" id="child-pick" value={childId} onChange={(event) => setChildId(event.target.value)}><option value="">Выберите ребёнка</option>{children.filter((child) => !linked.has(child.id)).map((child) => <option key={child.id} value={child.id}>{child.last_name} {child.first_name}</option>)}</select>
      <label htmlFor="guardian-relation-type">Отношение</label><RelationSelect id="guardian-relation-type" value={relationType} change={setRelationType} />
      <Button disabled={busy || !childId} onClick={() => void run(() => childrenApi.link(childId, guardian.id, relationType))}>Связать</Button>
    </div>}</div>}
  </section>;
}
