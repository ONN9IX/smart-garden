"use client";

import { useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { ChildSummary, GuardianContext } from "@/types/teacher";
import { relationLabels } from "@/lib/presentation";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function GroupsPage() {
  const { groups, groupId, setGroupId, error: groupError } = useGroups();
  const [children, setChildren] = useState<ChildSummary[]>([]);
  const [guardians, setGuardians] = useState<GuardianContext[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!groupId) return;
    Promise.all([teacherApi.children(groupId), teacherApi.guardians(groupId)])
      .then(([nextChildren, nextGuardians]) => { setChildren(nextChildren); setGuardians(nextGuardians); setError(""); })
      .catch((reason) => setError(userMessage(reason)));
  }, [groupId]);
  return <TeacherPageFrame title="Мои группы" eyebrow="Назначенный контекст">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /></div>
    {(error || groupError) && <p className={styles.error}>{error || groupError}</p>}
    <div className={styles.grid}>
      <section className={styles.card}><h2>Дети</h2><ul className={styles.list}>{children.map((child) => <li className={styles.row} key={child.id}>{child.first_name} {child.last_name} {child.middle_name ?? ""}</li>)}</ul>{children.length === 0 && <p className={styles.muted}>В группе нет активных детей.</p>}</section>
      <section className={styles.card}><h2>Контакты родителей</h2><ul className={styles.list}>{guardians.map((guardian) => <li className={styles.row} key={`${guardian.id}-${guardian.child_id}`}><span>{guardian.last_name} {guardian.first_name}<br/><small>{relationLabels[guardian.relation_type]} · {guardian.can_message ? "можно написать" : "нет активного аккаунта"}</small></span><span>{guardian.phone ?? guardian.email ?? "Контакт не указан"}</span></li>)}</ul>{guardians.length === 0 && <p className={styles.muted}>Доступных контактов нет.</p>}</section>
    </div>
  </TeacherPageFrame>;
}
