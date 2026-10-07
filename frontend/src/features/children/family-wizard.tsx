"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import { groupsApi } from "@/lib/api/groups";
import { managementPeopleApi } from "@/lib/api/management-people";
import { userMessage } from "@/lib/api/client";
import { RELATION_LABELS, type Group, type RelationType } from "@/types/stage2";
import type { DuplicateMatch, FamilyGuardianInput, GuardianSearchMatch } from "@/types/people";

type ChildDraft = { first_name: string; last_name: string; middle_name: string; birth_date: string; group_id: string };
type GuardianDraft = { key: number; first_name: string; last_name: string; middle_name: string; phone: string; email: string; relation_type: RelationType };
type SelectedGuardian = GuardianSearchMatch & { relation_type: RelationType };
const emptyChild: ChildDraft = { first_name: "", last_name: "", middle_name: "", birth_date: "", group_id: "" };

export function FamilyWizard() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [child, setChild] = useState<ChildDraft>(emptyChild);
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [childDuplicates, setChildDuplicates] = useState<DuplicateMatch[]>([]);
  const [guardianDuplicates, setGuardianDuplicates] = useState<Array<{ key: number; matches: DuplicateMatch[] }>>([]);
  const [selected, setSelected] = useState<SelectedGuardian[]>([]);
  const [newGuardians, setNewGuardians] = useState<GuardianDraft[]>([]);
  const [guardianQuery, setGuardianQuery] = useState("");
  const [guardianMatches, setGuardianMatches] = useState<GuardianSearchMatch[]>([]);
  const [guardianSearchBusy, setGuardianSearchBusy] = useState(false);
  const [nextKey, setNextKey] = useState(1);

  useEffect(() => {
    void groupsApi.list().then((response) => setGroups(response.items)).catch((reason) => setError(userMessage(reason))).finally(() => setGroupsLoading(false));
  }, []);

  function updateChild(key: keyof ChildDraft, value: string) {
    setChild((current) => ({ ...current, [key]: value }));
    setChildDuplicates([]);
  }
  async function checkChild(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setChildDuplicates([]);
    try {
      const response = await managementPeopleApi.checkDuplicates({
        kind: "child", first_name: child.first_name, last_name: child.last_name,
        middle_name: child.middle_name || null, birth_date: child.birth_date,
      });
      if (response.matches.length) { setChildDuplicates(response.matches); return; }
      setStep(2);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  async function searchExisting() {
    if (guardianQuery.trim().length < 2) return;
    setGuardianSearchBusy(true); setError("");
    try { setGuardianMatches((await managementPeopleApi.searchGuardians(guardianQuery.trim())).matches); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setGuardianSearchBusy(false); }
  }
  function addExisting(match: GuardianSearchMatch) {
    if (selected.some((item) => item.id === match.id)) return;
    setSelected((items) => [...items, { ...match, relation_type: "other" }]);
    setGuardianDuplicates([]);
  }
  function addNewGuardian() {
    setNewGuardians((items) => [...items, { key: nextKey, first_name: "", last_name: "", middle_name: "", phone: "", email: "", relation_type: "other" }]);
    setNextKey((key) => key + 1); setGuardianDuplicates([]);
  }
  function updateNewGuardian(key: number, field: keyof GuardianDraft, value: string) {
    setNewGuardians((items) => items.map((item) => item.key === key ? { ...item, [field]: value } : item));
    setGuardianDuplicates([]);
  }
  async function checkGuardians(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setGuardianDuplicates([]);
    try {
      const results = await Promise.all(newGuardians.map(async (item) => ({
        key: item.key,
        matches: (await managementPeopleApi.checkDuplicates({
          kind: "guardian", first_name: item.first_name, last_name: item.last_name,
          middle_name: item.middle_name || null, phone: item.phone || null, email: item.email || null,
        })).matches,
      })));
      const duplicates = results.filter((item) => item.matches.length);
      if (duplicates.length) { setGuardianDuplicates(duplicates); return; }
      setStep(3);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  async function createFamily() {
    setBusy(true); setError("");
    const guardians: FamilyGuardianInput[] = [
      ...selected.map(({ id, relation_type }) => ({ guardian_id: id, relation_type })),
      ...newGuardians.map((item) => ({
        new_guardian: {
          first_name: item.first_name.trim(), last_name: item.last_name.trim(),
          middle_name: item.middle_name.trim() || null, phone: item.phone.trim() || null, email: item.email.trim() || null,
        }, relation_type: item.relation_type,
      })),
    ];
    try {
      const result = await managementPeopleApi.createFamily({
        child: { ...child, first_name: child.first_name.trim(), last_name: child.last_name.trim(), middle_name: child.middle_name.trim() || null },
        guardians,
      });
      router.push(`/children/${result.id}`);
    } catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }

  if (groupsLoading) return <Loading />;
  return <div className="family-wizard">
    <ol className="wizard-steps" aria-label="Шаги создания семьи"><li aria-current={step === 1 ? "step" : undefined}>1 · Ребёнок</li><li aria-current={step === 2 ? "step" : undefined}>2 · Представители</li><li aria-current={step === 3 ? "step" : undefined}>3 · Проверка</li></ol>
    {error && <Alert>{error}</Alert>}
    {step === 1 && <form className="card section-card" onSubmit={(event) => void checkChild(event)}><h2>Данные ребёнка</h2><div className="form-grid">
      <label>Фамилия *<Input required maxLength={100} value={child.last_name} onChange={(event) => updateChild("last_name", event.target.value)} /></label>
      <label>Имя *<Input required maxLength={100} value={child.first_name} onChange={(event) => updateChild("first_name", event.target.value)} /></label>
      <label>Отчество<Input maxLength={100} value={child.middle_name} onChange={(event) => updateChild("middle_name", event.target.value)} /></label>
      <label>Дата рождения *<Input type="date" required value={child.birth_date} onChange={(event) => updateChild("birth_date", event.target.value)} /></label>
      <label>Группа *<select className="input" required value={child.group_id} onChange={(event) => updateChild("group_id", event.target.value)}><option value="">Выберите группу</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
    </div>
      {groups.length === 0 && <p className="empty-state">Нет активных групп. <Link className="text-link" href="/groups">Создайте группу перед добавлением ребёнка.</Link></p>}
      {childDuplicates.length > 0 && <div className="duplicate-warning"><h3>Найдены похожие карточки</h3><p>Сверьте ФИО и дату рождения. Совпадение не объединяет записи.</p><ul>{childDuplicates.map((match) => <li key={match.id}><Link className="text-link" href={`/children/${match.id}`}>{match.full_name}</Link>{match.context && ` · ${match.context}`}</li>)}</ul><Button type="button" disabled={busy} onClick={() => { setChildDuplicates([]); setStep(2); }}>Продолжить с отдельной карточкой</Button></div>}
      {childDuplicates.length === 0 && <Button disabled={busy || groups.length === 0}>{busy ? "Проверка..." : "Далее: представители"}</Button>}
    </form>}

    {step === 2 && <form className="card section-card" onSubmit={(event) => void checkGuardians(event)}><h2>Представители ребёнка</h2><p className="muted">Можно добавить существующие карточки, создать новые или продолжить без представителей.</p>
      <div className="field"><label htmlFor="family-guardian-search">Найти существующего представителя</label><div className="search-row"><Input id="family-guardian-search" value={guardianQuery} onChange={(event) => setGuardianQuery(event.target.value)} /><Button type="button" variant="secondary" disabled={guardianSearchBusy || guardianQuery.trim().length < 2} onClick={() => void searchExisting()}>{guardianSearchBusy ? "Поиск..." : "Найти"}</Button></div></div>
      {guardianMatches.length > 0 && <ul className="record-list">{guardianMatches.map((match) => <li key={match.id}><div className="record-link"><strong>{match.full_name}</strong><span className="muted">{[match.phone, match.email].filter(Boolean).join(" · ") || "Контакты не указаны"}</span><Button type="button" variant="secondary" disabled={selected.some((item) => item.id === match.id)} onClick={() => addExisting(match)}>{selected.some((item) => item.id === match.id) ? "Добавлен" : "Добавить"}</Button></div></li>)}</ul>}
      {selected.length > 0 && <section className="family-contacts"><h3>Выбранные представители</h3>{selected.map((item) => <div className="family-contact-row" key={item.id}><span>{item.full_name}</span><label>Связь<select className="input" value={item.relation_type} onChange={(event) => { setSelected((items) => items.map((current) => current.id === item.id ? { ...current, relation_type: event.target.value as RelationType } : current)); setGuardianDuplicates([]); }}>{Object.entries(RELATION_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><Button type="button" variant="secondary" onClick={() => setSelected((items) => items.filter((current) => current.id !== item.id))}>Убрать</Button></div>)}</section>}
      <section className="family-contacts"><div className="section-heading"><h3>Новая карточка представителя</h3><Button type="button" variant="secondary" onClick={addNewGuardian}>Добавить</Button></div>
        {newGuardians.length === 0 && <p className="muted">Новые карточки не добавлены.</p>}
        {newGuardians.map((item) => <fieldset className="family-guardian-card" key={item.key}><legend>Представитель {item.key}</legend><div className="form-grid">
          <label>Фамилия *<Input required maxLength={100} value={item.last_name} onChange={(event) => updateNewGuardian(item.key, "last_name", event.target.value)} /></label>
          <label>Имя *<Input required maxLength={100} value={item.first_name} onChange={(event) => updateNewGuardian(item.key, "first_name", event.target.value)} /></label>
          <label>Отчество<Input maxLength={100} value={item.middle_name} onChange={(event) => updateNewGuardian(item.key, "middle_name", event.target.value)} /></label>
          <label>Телефон<Input type="tel" maxLength={32} value={item.phone} onChange={(event) => updateNewGuardian(item.key, "phone", event.target.value)} /></label>
          <label>Email<Input type="email" maxLength={254} value={item.email} onChange={(event) => updateNewGuardian(item.key, "email", event.target.value)} /></label>
          <label>Связь с ребёнком<select className="input" value={item.relation_type} onChange={(event) => updateNewGuardian(item.key, "relation_type", event.target.value as RelationType)}>{Object.entries(RELATION_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        </div><Button type="button" variant="secondary" onClick={() => { setNewGuardians((items) => items.filter((current) => current.key !== item.key)); setGuardianDuplicates([]); }}>Убрать карточку</Button></fieldset>)}
      </section>
      {guardianDuplicates.length > 0 && <div className="duplicate-warning"><h3>Проверьте похожие карточки</h3><p>Можно открыть найденный профиль или продолжить без объединения.</p>{guardianDuplicates.map(({ key, matches }) => <ul key={key}>{matches.map((match) => <li key={match.id}><Link className="text-link" href={`/guardians/${match.id}`}>{match.full_name}</Link>{match.context && ` · ${match.context}`}</li>)}</ul>)}<Button type="button" disabled={busy} onClick={() => { setGuardianDuplicates([]); setStep(3); }}>Продолжить без объединения</Button></div>}
      <div className="action-row"><Button type="button" variant="secondary" onClick={() => { setStep(1); setGuardianDuplicates([]); }}>Назад</Button>{guardianDuplicates.length === 0 && <Button disabled={busy}>{busy ? "Проверка..." : "Далее: проверка"}</Button>}</div>
    </form>}

    {step === 3 && <section className="card section-card"><h2>Проверьте данные перед созданием</h2><dl className="profile-facts"><div><dt>Ребёнок</dt><dd>{[child.last_name, child.first_name, child.middle_name].filter(Boolean).join(" ")}</dd></div><div><dt>Дата рождения</dt><dd>{child.birth_date}</dd></div><div><dt>Группа</dt><dd>{groups.find((group) => group.id === child.group_id)?.name}</dd></div><div><dt>Представители</dt><dd>{[...selected.map((item) => `${item.full_name} — ${RELATION_LABELS[item.relation_type]}`), ...newGuardians.map((item) => `${item.last_name} ${item.first_name} — ${RELATION_LABELS[item.relation_type]}`)].join("; ") || "Не добавлены"}</dd></div></dl><p className="muted">Создание ребёнка, новых представителей и всех связей выполняется одной транзакцией.</p><div className="action-row"><Button variant="secondary" disabled={busy} onClick={() => setStep(2)}>Назад</Button><Button disabled={busy} onClick={() => void createFamily()}>{busy ? "Создание..." : "Создать ребёнка и связи"}</Button></div></section>}
  </div>;
}
