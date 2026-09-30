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
  return <AuthGate route="teacher"><AppShell><div className={styles.stack}>
    <div className="page-heading">{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1></div>
    {children}
  </div></AppShell></AuthGate>;
}

export function useGroups() {
  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [groupId, setGroupId] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { teacherApi.groups().then((items) => {
    setGroups(items); setGroupId((current) => current || items[0]?.id || "");
  }).catch((reason) => setError(userMessage(reason))); }, []);
  return { groups, groupId, setGroupId, error };
}

export function GroupPicker({ groups, groupId, setGroupId }: {
  groups: GroupSummary[]; groupId: string; setGroupId: (id: string) => void;
}) {
  return <label>Группа<select value={groupId} onChange={(event) => setGroupId(event.target.value)}>
    {groups.length === 0 && <option value="">Нет назначенных групп</option>}
    {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
  </select></label>;
}

export { styles };
