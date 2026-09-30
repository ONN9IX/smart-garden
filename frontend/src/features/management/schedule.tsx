"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { groupsApi } from "@/lib/api/groups";
import { managementApi } from "@/lib/api/management";
import { userMessage } from "@/lib/api/client";
import type { Group } from "@/types/stage2";
import type { ScheduleItem } from "@/types/management";
import { ManagerPage, useQueryParam } from "./common";

const weekdayLabels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export function SchedulePage() {
  return <ManagerPage><ScheduleContent /></ManagerPage>;
}

function ScheduleContent() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [weekday, setWeekday] = useState(0);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("active");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useQueryParam("group_id", setGroupId);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [groupList, schedule] = await Promise.all([
        groupsApi.list("active"),
        managementApi.schedule(groupId || undefined, status),
      ]);
      setGroups(groupList.items);
      setItems(schedule.items);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setLoading(false); }
  }, [groupId, status]);

  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!groupId) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await managementApi.createSchedule({
        group_id: groupId,
        weekday,
        start_time: startTime,
        end_time: endTime,
        title: title.trim(),
      });
      setTitle("");
      setMessage("Событие расписания создано.");
      await load();
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  async function edit(item: ScheduleItem) {
    const value = window.prompt("Новое название", item.title);
    if (value == null || !value.trim()) return;
    setBusy(true); setError("");
    try { await managementApi.updateSchedule(item.id, { title: value.trim() }); await load(); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><span className="eyebrow">Управление</span><h1>Расписание</h1><p>Недельное расписание групп.</p></div>
    <div className="filter-row">
      <label>Группа <select className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Все группы</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>Статус <select className="input" value={status} onChange={(event) => setStatus(event.target.value)}><option value="active">Активные</option><option value="archived">Архив</option><option value="all">Все</option></select></label>
    </div>
    {error && <Alert>{error}</Alert>}{message && <Alert tone="success">{message}</Alert>}
    <form className="card section-card" onSubmit={(event) => void create(event)}><h2>Добавить занятие</h2><div className="form-grid">
      <label>Группа <select required className="input" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Выберите</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <label>День <select className="input" value={weekday} onChange={(event) => setWeekday(Number(event.target.value))}>{weekdayLabels.map((label, index) => <option key={label} value={index}>{label}</option>)}</select></label>
      <label>Начало <Input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} /></label>
      <label>Окончание <Input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} /></label>
      <label>Название <Input required maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
    </div><Button disabled={busy || !groupId}>{busy ? "Сохранение..." : "Добавить"}</Button></form>
    {loading ? <Loading /> : items.length === 0 ? <p className="empty-state">События расписания не найдены.</p> : <ul className="record-list">{items.map((item) => <li key={item.id}><div className="record-link">
      <strong>{weekdayLabels[item.weekday]} · {item.start_time.slice(0, 5)}–{item.end_time.slice(0, 5)} · {item.title}</strong>
      <span className="muted">{item.status === "active" ? "Активно" : "Архив"}</span>
      {item.status === "active" && <span className="action-row"><Button variant="secondary" disabled={busy} onClick={() => void edit(item)}>Изменить</Button><Button variant="secondary" disabled={busy} onClick={() => {
        if (!window.confirm("Архивировать событие расписания?")) return;
        void managementApi.archiveSchedule(item.id).then(load).catch((reason) => setError(userMessage(reason)));
      }}>Архивировать</Button></span>}
    </div></li>)}</ul>}
  </>;
}
