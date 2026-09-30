"use client";

/* eslint-disable @next/next/no-img-element */

import { FormEvent, useCallback, useEffect, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { ChildSummary, PhotoAsset, PhotoConsent } from "@/types/teacher";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function PhotosPage() {
  const { groups, groupId, setGroupId } = useGroups(); const [children, setChildren] = useState<ChildSummary[]>([]);
  const [consents, setConsents] = useState<PhotoConsent[]>([]); const [items, setItems] = useState<PhotoAsset[]>([]);
  const [selected, setSelected] = useState<string[]>([]); const [file, setFile] = useState<File | null>(null); const [error, setError] = useState("");
  const load = useCallback(() => { if (!groupId) return; Promise.all([teacherApi.children(groupId), teacherApi.consents(groupId), teacherApi.photos(groupId)]).then(([nextChildren, nextConsents, nextItems]) => { setChildren(nextChildren); setConsents(nextConsents); setItems(nextItems); }).catch((reason) => setError(userMessage(reason))); }, [groupId]);
  useEffect(load, [load]);
  async function submit(event: FormEvent) { event.preventDefault(); if (!file) return; try { await teacherApi.uploadPhoto(groupId, selected, file); setFile(null); setSelected([]); load(); } catch (reason) { setError(userMessage(reason)); } }
  return <TeacherPageFrame title="Фото группы"><p className={styles.muted}>Фото доступны только через защищённый кабинет и при действующем согласии для каждого отмеченного ребёнка.</p><div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={setGroupId} /></div>{error && <p className={styles.error}>{error}</p>}<section className={styles.card}><form className={styles.stack} onSubmit={(event) => void submit(event)}><div className={styles.grid}>{children.map((child) => { const granted = consents.some((item) => item.child_id === child.id && item.status === "granted" && (!item.effective_to || new Date(item.effective_to) > new Date())); return <label key={child.id}><input type="checkbox" disabled={!granted} checked={selected.includes(child.id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, child.id] : current.filter((id) => id !== child.id))} /> {child.last_name} {child.first_name} {granted ? "" : "— нет согласия"}</label>; })}</div><input type="file" accept="image/png,image/jpeg" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><button className={styles.button} disabled={!file || selected.length === 0}>Загрузить синтетическое фото</button></form></section><div className={styles.grid}>{items.map((item) => <section className={styles.card} key={item.id}><img className={styles.photo} src={teacherApi.photoContent(item.id)} alt="Фото группы" /><p>{Math.round(item.size_bytes / 1024)} КБ · детей: {item.child_ids.length}</p></section>)}</div></TeacherPageFrame>;
}
