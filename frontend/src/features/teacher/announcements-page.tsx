"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { userMessage } from "@/lib/api/client";
import { teacherApi } from "@/lib/api/teacher";
import type { AnnouncementV2 } from "@/types/teacher";
import { announcementStatusLabels } from "@/lib/presentation";
import { GroupPicker, styles, TeacherPageFrame, useGroups } from "./shared";

export function AnnouncementsPage() {
  const { groups, groupId, setGroupId } = useGroups();
  const [items, setItems] = useState<AnnouncementV2[]>([]);
  const [editingId, setEditingId] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<"all" | "parents" | "staff">("parents");
  const [error, setError] = useState("");
  const [titleError, setTitleError] = useState("");
  const [bodyError, setBodyError] = useState("");
  const [showArchive, setShowArchive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<{ recipient_count: number; parents_count: number; staff_count: number } | null>(null);
  const [previewFor, setPreviewFor] = useState("");
  const [confirmedPreviewFor, setConfirmedPreviewFor] = useState("");
  const submitting = useRef(false);
  const previewKey = JSON.stringify([groupId, audience, title.trim(), body.trim()]);
  const hasCurrentPreview = Boolean(preview && previewFor === previewKey);

  const load = useCallback(() => {
    if (!groupId) return;
    teacherApi.v2Announcements("all").then((result) => { setItems(result.filter((item) => item.target_type === "group" && item.group_id === groupId)); setError(""); }).catch((reason) => setError(userMessage(reason)));
  }, [groupId]);
  useEffect(load, [load]);

  function clearForm() {
    setEditingId("");
    setTitle("");
    setBody("");
    setTitleError("");
    setBodyError("");
    setPreview(null);
    setPreviewFor("");
    setConfirmedPreviewFor("");
  }

  async function reviewAudience() {
    if (!groupId) { setError("Выберите группу."); return; }
    if (!title.trim() || !body.trim()) { setError("Сначала заполните заголовок и текст объявления."); return; }
    setBusy(true); setError(""); setConfirmedPreviewFor("");
    try {
      const result = await teacherApi.previewV2Announcement({
        target_type: "group", group_id: groupId, audience,
      });
      setPreview(result); setPreviewFor(previewKey);
    } catch (reason) { setPreview(null); setPreviewFor(""); setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    const missingTitle = !title.trim();
    const missingBody = !body.trim();
    setTitleError(missingTitle ? "Введите заголовок" : "");
    setBodyError(missingBody ? "Введите текст объявления" : "");
    if (missingTitle || missingBody) return;
    if (!editingId && (!hasCurrentPreview || confirmedPreviewFor !== previewKey)) {
      setError("Проверьте аудиторию и подтвердите число получателей перед публикацией."); return;
    }
    submitting.current = true;
    setBusy(true);
    try {
      if (editingId) await teacherApi.updateV2Announcement(editingId, { title: title.trim(), body: body.trim() });
      else await teacherApi.createV2Announcement({ target_type: "group", group_id: groupId, audience, title: title.trim(), body: body.trim() });
      clearForm();
      load();
      setError("");
    } catch (reason) {
      setError(userMessage(reason));
    } finally { submitting.current = false; setBusy(false); }
  }

  async function archive(id: string) {
    try {
      await teacherApi.archiveV2Announcement(id);
      if (editingId === id) clearForm();
      load();
    } catch (reason) {
      setError(userMessage(reason));
    }
  }

  return <TeacherPageFrame title="Объявления группы">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={(id) => { setGroupId(id); clearForm(); }} /></div>
    {error && <p className={styles.error}>{error}</p>}
    <section className={styles.card}>
      <form className={styles.toolbar} onSubmit={(event) => void submit(event)}>
        {!editingId && <label>Аудитория<select value={audience} onChange={(event) => setAudience(event.target.value as typeof audience)}><option value="parents">Родители</option><option value="staff">Сотрудники</option><option value="all">Все участники</option></select></label>}
        <label>Заголовок<input aria-invalid={Boolean(titleError)} value={title} maxLength={120} onChange={(event) => { setTitle(event.target.value); if (event.target.value.trim()) setTitleError(""); }} />{titleError && <small className={styles.error}>{titleError}</small>}</label>
        <label>Текст<textarea aria-invalid={Boolean(bodyError)} value={body} maxLength={2000} onChange={(event) => { setBody(event.target.value); if (event.target.value.trim()) setBodyError(""); }} />{bodyError && <small className={styles.error}>{bodyError}</small>}</label>
        {!editingId && <><button type="button" className={styles.buttonSecondary} disabled={busy} onClick={() => void reviewAudience()}>{busy ? "Проверяем аудиторию..." : "Проверить аудиторию"}</button>
          {hasCurrentPreview && preview && <div aria-live="polite">
            <strong>Проверка перед публикацией</strong>
            <p>{groups.find((group) => group.id === groupId)?.name || "Выбранная группа"} · {audience === "parents" ? "Родители" : audience === "staff" ? "Сотрудники" : "Все участники"}</p>
            <p>Получателей: {preview.recipient_count} (родители: {preview.parents_count}, сотрудники: {preview.staff_count}). Список людей не раскрывается.</p>
            <label><input type="checkbox" checked={confirmedPreviewFor === previewKey} onChange={(event) => setConfirmedPreviewFor(event.target.checked ? previewKey : "")} /> Подтверждаю выбранную аудиторию и число получателей</label>
          </div>}
        </>}
        <button className={styles.button} disabled={Boolean(busy || (!editingId && title.trim() && body.trim() && (!hasCurrentPreview || confirmedPreviewFor !== previewKey)))}>{busy ? "Сохранение..." : editingId ? "Сохранить изменения" : "Опубликовать для группы"}</button>
        {editingId && <button type="button" className={styles.buttonSecondary} onClick={clearForm}>Отмена</button>}
      </form>
      <div className={styles.toolbar}><button type="button" className={showArchive ? styles.buttonSecondary : styles.button} onClick={() => setShowArchive(false)}>Активные</button><button type="button" className={showArchive ? styles.button : styles.buttonSecondary} onClick={() => setShowArchive(true)}>Архив</button></div>
      <ul className={styles.list}>{items.filter((item) => showArchive ? item.status === "archived" : item.status === "active").map((item) => {
        const canManage = item.can_manage && item.status === "active";
        return <li className={styles.row} key={item.id}>
          <span><strong>{item.title}</strong><br/>{item.body}<small className={styles.threadPreview}>{item.audience === "parents" ? "Родители" : item.audience === "staff" ? "Сотрудники" : "Все участники"} · получателей: {item.recipient_count}</small></span>
          <span><small>{announcementStatusLabels[item.status]}</small>{canManage && <span className={styles.toolbar}>
            <button type="button" className={styles.buttonSecondary} onClick={() => { setEditingId(item.id); setTitle(item.title); setBody(item.body); }}>Изменить</button>
            <button type="button" className={styles.buttonSecondary} onClick={() => void archive(item.id)}>Архивировать</button>
          </span>}</span>
        </li>;
      })}</ul>
    </section>
  </TeacherPageFrame>;
}
