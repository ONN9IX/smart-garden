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
  const [previewBusy, setPreviewBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState<{ recipient_count: number; parents_count: number; staff_count: number } | null>(null);
  const [previewFor, setPreviewFor] = useState("");
  const [confirmedPreviewFor, setConfirmedPreviewFor] = useState("");
  const submitting = useRef(false);
  const currentGroupId = useRef(groupId);
  const loadSequence = useRef(0);
  const previewSequence = useRef(0);
  const previewKey = JSON.stringify([groupId, audience, title.trim(), body.trim()]);
  const hasCurrentPreview = Boolean(preview && previewFor === previewKey);

  const load = useCallback(() => {
    const requestedGroupId = groupId;
    const request = ++loadSequence.current;
    currentGroupId.current = requestedGroupId;
    if (!requestedGroupId) return;
    teacherApi.v2Announcements("all").then((result) => {
      if (request !== loadSequence.current || currentGroupId.current !== requestedGroupId) return;
      setItems(result.filter((item) => item.target_type === "group" && item.group_id === requestedGroupId));
      setError("");
    }).catch((reason) => {
      if (request !== loadSequence.current || currentGroupId.current !== requestedGroupId) return;
      setItems([]);
      setError(userMessage(reason));
    });
  }, [groupId]);
  useEffect(() => {
    void load();
    return () => { loadSequence.current += 1; previewSequence.current += 1; };
  }, [load]);

  function selectGroup(id: string) {
    currentGroupId.current = id;
    loadSequence.current += 1;
    previewSequence.current += 1;
    setItems([]);
    setError("");
    setPreviewBusy(false);
    clearForm();
    setGroupId(id);
  }

  function clearForm() {
    previewSequence.current += 1;
    setPreviewBusy(false);
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
    const requestGroupId = groupId;
    const requestKey = previewKey;
    const request = ++previewSequence.current;
    setPreviewBusy(true); setError(""); setConfirmedPreviewFor("");
    try {
      const result = await teacherApi.previewV2Announcement({
        target_type: "group", group_id: requestGroupId, audience,
      });
      if (request !== previewSequence.current || currentGroupId.current !== requestGroupId) return;
      setPreview(result); setPreviewFor(requestKey);
    } catch (reason) {
      if (request !== previewSequence.current || currentGroupId.current !== requestGroupId) return;
      setPreview(null); setPreviewFor(""); setError(userMessage(reason));
    } finally {
      if (request === previewSequence.current) setPreviewBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const requestGroupId = groupId;
    if (submitting.current || !requestGroupId || currentGroupId.current !== requestGroupId) return;
    const missingTitle = !title.trim();
    const missingBody = !body.trim();
    setTitleError(missingTitle ? "Введите заголовок" : "");
    setBodyError(missingBody ? "Введите текст объявления" : "");
    if (missingTitle || missingBody) return;
    if (editingId && !items.some((item) => item.id === editingId && item.group_id === requestGroupId)) {
      setError("Объявление недоступно в выбранной группе.");
      clearForm();
      return;
    }
    if (!editingId && (!hasCurrentPreview || confirmedPreviewFor !== previewKey)) {
      setError("Проверьте аудиторию и подтвердите число получателей перед публикацией."); return;
    }
    submitting.current = true;
    setSaving(true);
    try {
      if (currentGroupId.current !== requestGroupId) return;
      if (editingId) await teacherApi.updateV2Announcement(editingId, { title: title.trim(), body: body.trim() });
      else await teacherApi.createV2Announcement({ target_type: "group", group_id: requestGroupId, audience, title: title.trim(), body: body.trim() });
      if (currentGroupId.current === requestGroupId) {
        clearForm();
        load();
        setError("");
      }
    } catch (reason) {
      if (currentGroupId.current === requestGroupId) setError(userMessage(reason));
    } finally { submitting.current = false; setSaving(false); }
  }

  async function archive(id: string) {
    const requestGroupId = groupId;
    if (!requestGroupId || currentGroupId.current !== requestGroupId || !items.some((item) => item.id === id && item.group_id === requestGroupId && item.can_manage)) return;
    try {
      await teacherApi.archiveV2Announcement(id);
      if (currentGroupId.current === requestGroupId) {
        if (editingId === id) clearForm();
        load();
      }
    } catch (reason) {
      if (currentGroupId.current === requestGroupId) setError(userMessage(reason));
    }
  }

  return <TeacherPageFrame title="Объявления группы">
    <div className={styles.toolbar}><GroupPicker groups={groups} groupId={groupId} setGroupId={selectGroup} /></div>
    {error && <p className={styles.error}>{error}</p>}
    <section className={styles.card}>
      <form className={styles.toolbar} onSubmit={(event) => void submit(event)}>
        {!editingId && <label>Аудитория<select value={audience} onChange={(event) => { previewSequence.current += 1; setPreviewBusy(false); setAudience(event.target.value as typeof audience); }}><option value="parents">Родители</option><option value="staff">Сотрудники</option><option value="all">Все участники</option></select></label>}
        <label>Заголовок<input aria-invalid={Boolean(titleError)} value={title} maxLength={120} onChange={(event) => { previewSequence.current += 1; setPreviewBusy(false); setTitle(event.target.value); if (event.target.value.trim()) setTitleError(""); }} />{titleError && <small className={styles.error}>{titleError}</small>}</label>
        <label>Текст<textarea aria-invalid={Boolean(bodyError)} value={body} maxLength={2000} onChange={(event) => { previewSequence.current += 1; setPreviewBusy(false); setBody(event.target.value); if (event.target.value.trim()) setBodyError(""); }} />{bodyError && <small className={styles.error}>{bodyError}</small>}</label>
        {!editingId && <><button type="button" className={styles.buttonSecondary} disabled={previewBusy || saving} onClick={() => void reviewAudience()}>{previewBusy ? "Проверяем аудиторию..." : "Проверить аудиторию"}</button>
          {hasCurrentPreview && preview && <div aria-live="polite">
            <strong>Проверка перед публикацией</strong>
            <p>{groups.find((group) => group.id === groupId)?.name || "Выбранная группа"} · {audience === "parents" ? "Родители" : audience === "staff" ? "Сотрудники" : "Все участники"}</p>
            <p>Получателей: {preview.recipient_count} (родители: {preview.parents_count}, сотрудники: {preview.staff_count}). Список людей не раскрывается.</p>
            <label><input type="checkbox" checked={confirmedPreviewFor === previewKey} onChange={(event) => setConfirmedPreviewFor(event.target.checked ? previewKey : "")} /> Подтверждаю выбранную аудиторию и число получателей</label>
          </div>}
        </>}
        <button className={styles.button} disabled={Boolean(saving || previewBusy || (!editingId && title.trim() && body.trim() && (!hasCurrentPreview || confirmedPreviewFor !== previewKey)))}>{saving ? "Сохранение..." : editingId ? "Сохранить изменения" : "Опубликовать для группы"}</button>
        {editingId && <button type="button" className={styles.buttonSecondary} onClick={clearForm}>Отмена</button>}
      </form>
      <div className={styles.toolbar}><button type="button" className={showArchive ? styles.buttonSecondary : styles.button} onClick={() => setShowArchive(false)}>Активные</button><button type="button" className={showArchive ? styles.button : styles.buttonSecondary} onClick={() => setShowArchive(true)}>Архив</button></div>
      <ul className={styles.list}>{items.filter((item) => item.group_id === groupId && (showArchive ? item.status === "archived" : item.status === "active")).map((item) => {
        const canManage = item.can_manage && item.status === "active";
        return <li className={styles.row} key={item.id}>
          <span><strong>{item.title}</strong><br/>{item.body}<small className={styles.threadPreview}>{item.audience === "parents" ? "Родители" : item.audience === "staff" ? "Сотрудники" : "Все участники"} · получателей: {item.recipient_count}</small></span>
          <span><small>{announcementStatusLabels[item.status]}</small>{canManage && <span className={styles.toolbar}>
            <button type="button" className={styles.buttonSecondary} onClick={() => { if (currentGroupId.current !== item.group_id) return; setEditingId(item.id); setTitle(item.title); setBody(item.body); }}>Изменить</button>
            <button type="button" className={styles.buttonSecondary} onClick={() => void archive(item.id)}>Архивировать</button>
          </span>}</span>
        </li>;
      })}</ul>
    </section>
  </TeacherPageFrame>;
}
