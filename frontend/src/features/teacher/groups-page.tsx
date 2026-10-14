"use client";

import { useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { ChildSummary, GuardianContext } from "@/types/teacher";
import { relationLabels } from "@/lib/presentation";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";
import { useAuth } from "@/features/auth/auth-provider";
import { organizationTerms } from "@/lib/organization-terminology";

export function GroupsPage() {
  const { current } = useAuth();
  const terms = organizationTerms(current?.organization.operating_profile ?? "KINDERGARTEN");
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [guardians, setGuardians] = useState<GuardianContext[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    let version = 0;
    const load = () => {
      const request = ++version;
      setChildren([]); setGuardians([]); setError(""); setLoading(Boolean(groupId));
      if (!groupId) return;
      Promise.all([teacherApi.children(groupId), teacherApi.guardians(groupId)])
        .then(([nextChildren, nextGuardians]) => { if (active && request === version) { setChildren(nextChildren); setGuardians(nextGuardians); } })
        .catch((reason) => { if (active && request === version) setError(userMessage(reason)); })
        .finally(() => { if (active && request === version) setLoading(false); });
    };
    void Promise.resolve().then(() => { if (active) load(); });
    window.addEventListener("focus", load);
    return () => { active = false; version += 1; window.removeEventListener("focus", load); };
  }, [groupId, revision]);
  return <TeacherPageFrame title={`Мои ${terms.groups}`} eyebrow="Назначенный контекст">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={(id) => { setChildren([]); setGuardians([]); setError(""); setGroupId(id); }} /></div>
    {(error || groupError) && <p className={styles.error} role="alert">{error || groupError}</p>}
    {error && <button className={styles.buttonSecondary} onClick={() => setRevision((value) => value + 1)}>Повторить загрузку</button>}
    {loading && <p className={styles.muted} role="status">Загружаем данные группы…</p>}
    <div className={styles.grid}>
      <section className={styles.card}><h2>{terms.children}</h2><ul className={styles.list}>{children.map((child) => <li className={styles.row} key={child.id}>{child.first_name} {child.last_name} {child.middle_name ?? ""}</li>)}</ul>{!loading && !error && children.length === 0 && <p className={styles.muted}>В группе нет активных {terms.children}.</p>}</section>
      <section className={styles.card}><h2>Контакты: {terms.guardians}</h2><ul className={styles.list}>{guardians.map((guardian) => <li className={styles.row} key={`${guardian.id}-${guardian.child_id}`}><span>{guardian.last_name} {guardian.first_name}<br/><small>{relationLabels[guardian.relation_type]} · {guardian.can_message ? "можно написать" : "нет активного аккаунта"}</small></span><span>{guardian.phone ?? guardian.email ?? "Контакт не указан"}</span></li>)}</ul>{!loading && !error && guardians.length === 0 && <p className={styles.muted}>Доступных контактов нет.</p>}</section>
    </div>
  </TeacherPageFrame>;
}
