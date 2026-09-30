"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { AuthGate } from "@/features/auth/auth-gate";
import { auditApi } from "@/lib/api/audit";
import { userMessage } from "@/lib/api/client";
import type { AuditEvent } from "@/types/stage4";

const entityTypes = [
  "group", "child", "guardian", "child_guardian", "employee", "user_account", "attendance", "announcement",
  "teacher_assignment", "group_schedule_item", "communication_message", "child_diary_entry", "poll",
  "incident", "teacher_task", "notification", "document_notice", "photo_consent", "photo_asset", "organization",
];
const actions = [
  "group.create", "group.update", "group.archive", "group.restore",
  "child.create", "child.update", "child.archive", "child.restore",
  "guardian.create", "guardian.update", "guardian.archive", "guardian.restore",
  "child_guardian.create", "child_guardian.update", "child_guardian.archive", "child_guardian.restore",
  "employee.create", "employee.update", "employee.archive", "employee.restore",
  "account.create", "account.reset_password", "account.block", "account.unblock",
  "teacher_account.create", "teacher_account.reset", "teacher_account.block", "teacher_account.unblock",
  "attendance.create", "attendance.update",
  "announcement.create", "announcement.update", "announcement.archive",
  "teacher_assignment.create", "teacher_assignment.archive", "teacher_assignment.restore",
  "schedule.create", "schedule.update", "schedule.archive",
  "teacher_message.create", "diary.create", "diary.update",
  "poll.create", "poll.close", "poll.vote",
  "incident.create", "incident.update", "incident.resolve",
  "teacher_task.create", "teacher_task.update", "teacher_task.cancel", "teacher_task.status",
  "notification.read", "document_notice.issue", "document_notice.ack",
  "photo_consent.record", "photo_consent.withdraw", "photo.create", "photo.restrict", "photo.remove",
  "organization.settings_update",
];
const detailLabels: Record<string, string> = {
  changed_fields: "Изменённые поля", status_before: "Статус до", status_after: "Статус после",
  account_role: "Роль аккаунта", relation_type: "Тип связи", child_id: "ID ребёнка",
  guardian_id: "ID представителя", before: "До", after: "После",
  target_type: "Цель", group_id: "ID группы", thread_id: "ID чата",
  assignee_employee_id: "ID воспитателя", recipient_user_id: "ID получателя",
  requires_ack: "Требуется подтверждение", category: "Категория", scope: "Область согласия",
};
const actorRole: Record<string, string> = { DIRECTOR: "Директор", ADMIN: "Администратор", TEACHER: "Воспитатель", PARENT: "Родитель" };

function detailValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object" && value !== null) {
    return Object.entries(value).map(([key, item]) => `${key}: ${item ?? "—"}`).join("; ");
  }
  return value === null || value === undefined ? "—" : String(value);
}

function AuditDetails({ event }: { event: AuditEvent }) {
  const entries = Object.entries(event.details);
  if (entries.length === 0) return <span className="muted">—</span>;
  return <dl className="audit-details">{entries.map(([key, value]) => <div key={key}>
    <dt>{detailLabels[key] ?? key}</dt><dd>{detailValue(value)}</dd>
  </div>)}</dl>;
}

export function AuditPage() {
  return <AuthGate route="director"><AuditContent /></AuthGate>;
}

function AuditContent() {
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setItems([]);
      setError("Дата начала не может быть позже даты окончания.");
      setLoading(false);
      return;
    }
    try {
      const result = await auditApi.list({
        entity_type: entityType || undefined, action: action || undefined,
        date_from: dateFrom || undefined, date_to: dateTo || undefined, limit, offset,
      });
      setItems(result.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [action, dateFrom, dateTo, entityType, limit, offset]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  const resetPage = () => setOffset(0);
  const resetFilters = () => { setEntityType(""); setAction(""); setDateFrom(""); setDateTo(""); setLimit(50); setOffset(0); };

  return <AppShell>
    <div className="page-heading"><span className="eyebrow">Безопасность</span><h1>Журнал аудита</h1>
      <p>Неизменяемая история критичных действий в вашем детском саду.</p></div>
    <div className="filter-row">
      <label>Объект <select className="input" value={entityType} onChange={(event) => { resetPage(); setEntityType(event.target.value); }}>
        <option value="">Все объекты</option>{entityTypes.map((value) => <option key={value}>{value}</option>)}
      </select></label>
      <label>Действие <select className="input" value={action} onChange={(event) => { resetPage(); setAction(event.target.value); }}>
        <option value="">Все действия</option>{actions.map((value) => <option key={value}>{value}</option>)}
      </select></label>
      <label>С даты <Input type="date" value={dateFrom} onChange={(event) => { resetPage(); setDateFrom(event.target.value); }} /></label>
      <label>По дату <Input type="date" value={dateTo} onChange={(event) => { resetPage(); setDateTo(event.target.value); }} /></label>
      <label>На странице <select className="input" value={limit} onChange={(event) => { resetPage(); setLimit(Number(event.target.value)); }}>
        {[25, 50, 100].map((value) => <option key={value} value={value}>{value}</option>)}
      </select></label>
      <Button type="button" variant="secondary" onClick={resetFilters}>Сбросить фильтры</Button>
    </div>
    {error && <Alert>{error}</Alert>}
    {loading ? <Loading /> : error ? <Button variant="secondary" onClick={() => void load()}>Повторить</Button>
      : items.length === 0 ? <p className="empty-state">События не найдены.</p>
        : <div className="audit-table-wrap"><table className="audit-table">
          <thead><tr><th>Время</th><th>Пользователь</th><th>Действие</th><th>Объект</th><th>ID объекта</th><th>Детали</th></tr></thead>
          <tbody>{items.map((event) => <tr key={event.id}>
            <td>{new Date(event.created_at).toLocaleString("ru-RU")}</td>
            <td>{event.actor.username}<br /><span className="muted">{actorRole[event.actor.role]}</span></td>
            <td>{event.action}</td><td>{event.entity_type}</td>
            <td className="audit-id">{event.entity_id ?? "—"}</td><td><AuditDetails event={event} /></td>
          </tr>)}</tbody>
        </table></div>}
    <div className="audit-pagination" aria-label="Постраничная навигация">
      <Button variant="secondary" disabled={loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Назад</Button>
      <span>Записи {items.length === 0 ? 0 : offset + 1}–{offset + items.length}</span>
      <Button variant="secondary" disabled={loading || items.length < limit} onClick={() => setOffset(offset + limit)}>Далее</Button>
    </div>
  </AppShell>;
}
