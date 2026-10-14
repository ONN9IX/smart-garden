"use client";
import { useEffect, useState } from "react";
import { managementApi } from "@/lib/api/management";
import { groupsApi } from "@/lib/api/groups";
import { userMessage } from "@/lib/api/client";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

type Employee = { first_name: string; last_name: string; middle_name?: string | null; position: string; category: "teacher" | "administrator" | "other" };
type Schedule = { group_id: string; weekday: number; start_time: string; end_time: string; title: string };
const employeeSample = '[{"first_name":"Анна","last_name":"Иванова","position":"Тренер","category":"teacher"}]';
const scheduleSample = '[{"group_id":"UUID группы","weekday":1,"start_time":"10:00","end_time":"11:00","title":"Гимнастика"}]';

export function InitialSetupPage() {
  const [employees, setEmployees] = useState("[]");
  const [schedules, setSchedules] = useState("[]");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [availableGroups, setAvailableGroups] = useState<{ id: string; name: string }[]>([]);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof managementApi.previewInitialSetup>> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { void Promise.resolve().then(() => groupsApi.list("active")).then(result => setAvailableGroups(result.items.map(({ id, name }) => ({ id, name })))).catch(() => setAvailableGroups([])); }, []);
  async function requestPreview() {
    setBusy(true); setError(""); setPreview(null);
    try {
      const employeeRows = JSON.parse(employees) as Employee[];
      const scheduleRows = JSON.parse(schedules) as Schedule[];
      setPreview(await managementApi.previewInitialSetup({ idempotency_key: key, employees: employeeRows, schedules: scheduleRows }));
    } catch (e) { setError(userMessage(e, "Проверьте формат JSON и повторите.")); }
    finally { setBusy(false); }
  }
  async function apply() {
    if (!preview?.ready) return;
    setBusy(true); setError("");
    try {
      const result = await managementApi.applyInitialSetup({ idempotency_key: key, employees: JSON.parse(employees), schedules: JSON.parse(schedules), request_digest: preview.request_digest, confirmed: true });
      setError(`Настройка выполнена: сотрудников ${result.employee_count}, расписаний ${result.schedule_count}${result.replayed ? " (повторный запрос)" : ""}.`);
      setKey(crypto.randomUUID());
      setPreview(null);
    } catch (e) { setError(userMessage(e, "Не удалось применить настройку.")); }
    finally { setBusy(false); }
  }
  return <section className="page-container"><h1>Первоначальная настройка</h1>
    <p>Добавьте сотрудников и регулярное расписание пакетно. Учётные записи сотрудников не создаются и роли не назначаются. До применения проверьте каждую строку.</p>
    {error && <Alert>{error}</Alert>}
    <label>Сотрудники — JSON-массив (до 200 строк)<textarea rows={10} value={employees} onChange={e => { setEmployees(e.target.value); setPreview(null); }} /></label>
    <p>Поля: first_name, last_name, middle_name (необязательно), position, category (teacher / administrator / other). Пример: <code>{employeeSample}</code></p>
    <label>Недельное расписание — JSON-массив (до 500 строк)<textarea rows={10} value={schedules} onChange={e => { setSchedules(e.target.value); setPreview(null); }} /></label>
    <details><summary>Активные группы организации</summary>{availableGroups.length ? <ul>{availableGroups.map(group => <li key={group.id}>{group.name} — <code>{group.id}</code></li>)}</ul> : <p>Группы не загружены или ещё не созданы.</p>}</details>
    <p>Поля: group_id, weekday (0–6), start_time, end_time, title. Пример: <code>{scheduleSample}</code></p>
    <Button disabled={busy} onClick={() => void requestPreview()}>{busy ? "Проверяем…" : "Проверить пакет"}</Button>
    {preview && <div aria-live="polite"><h2>{preview.ready ? "Пакет готов" : "Найдены ошибки"}</h2>
      {[...preview.employee_rows.map(r => ({ ...r, kind: "Сотрудник" })), ...preview.schedule_rows.map(r => ({ ...r, kind: "Расписание" }))].map((r, i) => <p key={`${r.kind}-${i}`}>{r.kind} · строка {r.row}: {r.status === "ready" ? "готово" : r.message}</p>)}
      <Button disabled={!preview.ready || busy} onClick={() => void apply()}>Подтвердить и применить</Button>
    </div>}
  </section>;
}
