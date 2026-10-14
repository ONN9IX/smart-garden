"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { AuthGate } from "@/features/auth/auth-gate";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { GroupSummary } from "@/types/teacher";
import styles from "./cabinet.module.css";

export function TeacherPageFrame({ title, eyebrow, children }: {
  title: string; eyebrow?: string; children: React.ReactNode;
}) {
  return <AuthGate route="teacher"><div className={styles.teacherShell}><AppShell><div className={styles.stack}>
    <div className={styles.pageHeading}>{eyebrow && <span className={styles.eyebrow}>{eyebrow}</span>}<h1>{title}</h1></div>
    {children}
  </div></AppShell></div></AuthGate>;
}

export function useGroups(initialGroupId?: string) {
  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { teacherApi.groups().then((items) => {
    setGroups(items); setGroupId((current) => initialGroupId
      ? items.some((group) => group.id === initialGroupId) ? initialGroupId : ""
      : current || items[0]?.id || "");
  }).catch((reason) => setError(userMessage(reason))); }, [initialGroupId]);
  return { groups, groupId, setGroupId, error };
}

export function GroupPicker({ groups, groupId, setGroupId }: {
  groups: GroupSummary[]; groupId: string; setGroupId: (id: string) => void;
}) {
  return <label>Группа<select value={groupId} onChange={(event) => setGroupId(event.target.value)}>
    {(!groupId || groups.length === 0) && <option value="">{groups.length === 0 ? "Нет назначенных групп" : "Выберите назначенную группу"}</option>}
    {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
  </select></label>;
}

export { styles };
