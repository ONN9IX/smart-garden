"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { communicationsAnnouncementsApi } from "@/lib/api/announcements";
import { ApiError, userMessage } from "@/lib/api/client";
import { groupsApi } from "@/lib/api/groups";
import type { Group } from "@/types/stage2";
import type {
  AnnouncementStatusFilter,
  AnnouncementTarget,
  CommunicationsAnnouncement,
  CommunicationsAnnouncementAudience,
  CommunicationsAnnouncementFields,
} from "@/types/stage4";

const statusLabels = { active: "Активно", archived: "В архиве" };
const privacyNotice = "Не указывайте пароли, медицинские сведения и другие избыточные персональные данные.";

function createdAt(value: string) {
  return new Date(value).toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

function targetLabel(item: CommunicationsAnnouncement) {
  return item.target_type === "all" ? "Весь детский сад" : item.group_name ?? "Группа";
}

export function AnnouncementsPage() {
  return <AuthGate route="dashboard"><AnnouncementsContent /></AuthGate>;
}

function AnnouncementsContent() {
  const [status, setStatus] = useState<AnnouncementStatusFilter>("active");
  const [targetType, setTargetType] = useState<AnnouncementTarget | "">("");
  const [groupId, setGroupId] = useState("");
  const [groups, setGroups] = useState<Group[]>([]);
  const [items, setItems] = useState<CommunicationsAnnouncement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const loadVersion = useRef(0);
  const load = useCallback(async () => {
    const version = ++loadVersion.current;
    setLoading(true); setError("");
    try {
      const [result, groupList] = await Promise.all([
        communicationsAnnouncementsApi.list(status),
        groupsApi.list("active"),
      ]);
      if (version !== loadVersion.current) return;
      setItems(result.filter((item) => (!targetType || item.target_type === targetType) && (!groupId || item.group_id === groupId)));
      setGroups(groupList.items);
    }
    catch (reason) {
      if (version === loadVersion.current) setError(userMessage(reason));
    }
    finally {
      if (version === loadVersion.current) setLoading(false);
    }
  }, [groupId, status, targetType]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  return <AppShell>
    <div className="page-heading action-heading"><div><span className="eyebrow">Связь</span><h1>Объявления</h1><p>Оперативные публикации для всего сада или выбранной группы.</p></div>
      <Link href="/announcements/new" className="button button-primary">Создать объявление</Link></div>
    <div className="filter-row">
      <label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value as AnnouncementStatusFilter)}>
        <option value="active">Активные</option><option value="archived">Архив</option><option value="all">Все</option>
      </select></label>
      <label>Получатели <select className="input" value={targetType} onChange={(event) => { const value = event.target.value as AnnouncementTarget | ""; setTargetType(value); if (value !== "group") setGroupId(""); }}>
        <option value="">Все</option><option value="all">Весь детский сад</option><option value="group">Группа</option>
      </select></label>
      {targetType === "group" && <label>Группа <select aria-label="Фильтр по группе" className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Все группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>}
    </div>
    {error && <Alert>{error}</Alert>}
    {loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button>
      : items.length === 0 ? <p className="empty-state">Объявления не найдены.</p>
        : <ul className="announcement-list">{items.map((item) => <li key={item.id}>
          <Link href={`/announcements/${item.id}`} className="card announcement-card">
            <div><strong>{item.title}</strong><span>{targetLabel(item)} · {item.audience === "parents" ? "Родители" : item.audience === "staff" ? "Сотрудники" : "Все"}</span><span>Получателей: {item.recipient_count}</span></div>
            <div className="announcement-meta"><span>{statusLabels[item.status]}</span><time dateTime={item.published_at}>{createdAt(item.published_at)}</time></div>
          </Link>
        </li>)}</ul>}
  </AppShell>;
}

export function AnnouncementCreatePage() {
  return <AuthGate route="dashboard"><AnnouncementEditor /></AuthGate>;
}

export function AnnouncementDetailPage({ id }: { id: string }) {
  return <AuthGate route="dashboard"><AnnouncementEditor id={id} /></AuthGate>;
}

function AnnouncementEditor({ id }: { id?: string }) {
  const router = useRouter();
  const [item, setItem] = useState<CommunicationsAnnouncement | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [targetType, setTargetType] = useState<AnnouncementTarget>("all");
  const [audience, setAudience] = useState<CommunicationsAnnouncementAudience>("all");
  const [groupId, setGroupId] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(Boolean(id));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState<{ recipient_count: number; parents_count: number; staff_count: number } | null>(null);
  const [previewFor, setPreviewFor] = useState("");
  const [confirmedPreviewFor, setConfirmedPreviewFor] = useState("");
  const submitting = useRef(false);
  const createKey = useRef(crypto.randomUUID());
  const previewKey = JSON.stringify([targetType, groupId, audience, title.trim(), body.trim()]);
  const hasCurrentPreview = Boolean(preview && previewFor === previewKey);

  async function reviewAudience() {
    if (targetType === "group" && !groupId) { setError("Выберите группу."); return; }
    if (!title.trim() || !body.trim()) { setError("Сначала заполните заголовок и текст объявления."); return; }
    setBusy(true); setError(""); setMessage(""); setConfirmedPreviewFor("");
    try {
      const result = await communicationsAnnouncementsApi.preview({
        target_type: targetType, group_id: targetType === "group" ? groupId : null, audience,
      });
      setPreview(result); setPreviewFor(previewKey);
    } catch (reason) { setPreview(null); setPreviewFor(""); setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [groupList, announcement] = await Promise.all([
        groupsApi.list("active"),
        id ? communicationsAnnouncementsApi.get(id) : Promise.resolve(null),
      ]);
      setGroups(groupList.items);
      if (announcement) {
        setItem(announcement); setTargetType(announcement.target_type);
        setAudience(announcement.audience); setGroupId(announcement.group_id ?? ""); setTitle(announcement.title); setBody(announcement.body);
      }
    } catch (reason) {
      setError(reason instanceof ApiError && reason.status === 404 ? "Объявление не найдено." : userMessage(reason));
    } finally { setLoading(false); }
  }, [id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current || item?.status === "archived") return;
    if (targetType === "group" && !groupId) { setError("Выберите группу."); return; }
    if (!id && (!hasCurrentPreview || confirmedPreviewFor !== previewKey)) {
      setError("Проверьте аудиторию и подтвердите число получателей перед публикацией."); return;
    }
    submitting.current = true; setBusy(true); setError(""); setMessage("");
    const fields: CommunicationsAnnouncementFields = {
      target_type: targetType,
      group_id: targetType === "group" ? groupId : null,
      audience,
      title: title.trim(),
      body: body.trim(),
    };
    try {
      const saved = id ? await communicationsAnnouncementsApi.update(id, { title: fields.title, body: fields.body }) : await communicationsAnnouncementsApi.create(fields, createKey.current);
      setItem(saved); setTitle(saved.title); setBody(saved.body); setGroupId(saved.group_id ?? "");
      if (!id) router.replace(`/announcements/${saved.id}`);
      else setMessage("Объявление сохранено.");
    } catch (reason) { setError(userMessage(reason)); }
    finally { submitting.current = false; setBusy(false); }
  }

  async function archive() {
    if (!id || !item || busy || !window.confirm("Архивировать объявление? Вернуть его из архива будет нельзя.")) return;
    setBusy(true); setError(""); setMessage("");
    try { setItem(await communicationsAnnouncementsApi.archive(id)); setMessage("Объявление архивировано."); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  const archived = item?.status === "archived";
  const currentGroupMissing = item?.group_id && !groups.some((group) => group.id === item.group_id);
  return <AppShell><Link href="/announcements" className="text-link">← К объявлениям</Link>
    {loading ? <div className="section-space"><Loading /></div> : error && id && !item
      ? <div className="section-space"><Alert>{error}</Alert><Button variant="secondary" onClick={() => void load()}>Повторить</Button></div>
      : <><div className="page-heading section-space"><span className="eyebrow">{id ? archived ? "Архив" : "Активное объявление" : "Новая публикация"}</span>
        <h1>{id ? "Объявление" : "Создать объявление"}</h1><p>Публикация становится активной сразу после сохранения.</p></div>
        {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
        {archived && <Alert tone="success">Архивное объявление доступно только для чтения.</Alert>}
        <form className="card section-card announcement-form" onSubmit={(event) => void save(event)}>
          <FormField id="announcement-target" label="Получатели"><select id="announcement-target" className="input" value={targetType} disabled={Boolean(id) || archived} onChange={(event) => {
            const value = event.target.value as AnnouncementTarget; setTargetType(value); if (value === "all") setGroupId("");
          }}><option value="all">Весь детский сад</option><option value="group">Одна группа</option></select></FormField>
          {targetType === "group" && <FormField id="announcement-group" label="Группа"><select id="announcement-group" className="input" required value={groupId} disabled={Boolean(id) || archived} onChange={(event) => setGroupId(event.target.value)}>
            <option value="">Выберите группу</option>{currentGroupMissing && item?.group_id && <option value={item.group_id}>{item.group_name || "Группа"} (архив)</option>}
            {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
          </select></FormField>}
          <FormField id="announcement-audience" label="Аудитория"><select id="announcement-audience" className="input" value={audience} disabled={Boolean(id) || archived} onChange={(event) => setAudience(event.target.value as CommunicationsAnnouncementAudience)}><option value="all">Все участники</option><option value="parents">Родители</option><option value="staff">Сотрудники</option></select></FormField>
          {item && <p className="muted">Получателей: {item.recipient_count}. Список получателей не раскрывается.</p>}
          <FormField id="announcement-title" label="Заголовок"><Input id="announcement-title" maxLength={120} required readOnly={archived} value={title} onChange={(event) => setTitle(event.target.value)} /></FormField>
          <FormField id="announcement-body" label="Текст"><textarea id="announcement-body" className="input announcement-body" maxLength={2000} required readOnly={archived} value={body} onChange={(event) => setBody(event.target.value)} /></FormField>
          <p className="privacy-notice">{privacyNotice}</p>
          {!id && !archived && <div className="stack">
            <Button type="button" variant="secondary" disabled={busy} onClick={() => void reviewAudience()}>{busy ? "Проверяем аудиторию..." : "Проверить аудиторию"}</Button>
            {hasCurrentPreview && preview && <div className="card section-card" aria-live="polite">
              <strong>Проверка перед публикацией</strong>
              <span>{targetType === "all" ? "Весь детский сад" : groups.find((group) => group.id === groupId)?.name || "Выбранная группа"} · {audience === "parents" ? "Родители" : audience === "staff" ? "Сотрудники" : "Все участники"}</span>
              <span>Получателей: {preview.recipient_count} (родители: {preview.parents_count}, сотрудники: {preview.staff_count}). Список людей не раскрывается.</span>
              <label><input type="checkbox" checked={confirmedPreviewFor === previewKey} onChange={(event) => setConfirmedPreviewFor(event.target.checked ? previewKey : "")} /> Подтверждаю выбранную аудиторию и число получателей</label>
            </div>}
          </div>}
          {!archived && <div className="action-row"><Button type="submit" disabled={Boolean(busy || (!id && title.trim() && body.trim() && (!hasCurrentPreview || confirmedPreviewFor !== previewKey)))}>{busy ? "Сохранение..." : id ? "Сохранить" : "Опубликовать"}</Button>
            {id && <Button type="button" variant="secondary" disabled={busy} onClick={() => void archive()}>Архивировать</Button>}</div>}
        </form>
      </>}
  </AppShell>;
}
