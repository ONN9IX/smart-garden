"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { privacyApi, type Purpose } from "@/lib/api/privacy";
import { userMessage } from "@/lib/api/client";

/** A staff attestation of external documents, never a subject consent or signature. */
export function BasisConfirmation({ type, ids }: { type: "guardian" | "employee"; ids: string[] }) {
  const [purposes, setPurposes] = useState<Purpose[]>([]);
  const [purpose, setPurpose] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const selection = ids.join(",");
  useEffect(() => {
    let live = true;
    void privacyApi.me().then(data => { if (live) setPurposes(data.purposes.filter(p => p.ready && p.code === "account_access")); })
      .catch(() => { if (live) setError("Не удалось загрузить основания. Подтверждение недоступно."); });
    return () => { live = false; };
  }, []);
  // A changed selection requires a new deliberate attestation.
  useEffect(() => { void Promise.resolve().then(() => { setConfirmed(false); setMessage(""); }); }, [selection, purpose]);
  async function save() {
    if (!confirmed || !purpose || busy || !ids.length) return;
    setBusy(true); setError("");
    try { await privacyApi.attest(type, ids, purpose); setMessage("Подтверждение записано. Теперь можно отправить приглашение."); setConfirmed(false); }
    catch (reason) { setError(userMessage(reason)); }
    finally { setBusy(false); }
  }
  return <fieldset className="section-space"><legend>Основание предоставления доступа</legend>
    <p>До приглашения выберите утверждённое основание и подтвердите наличие необходимых документов. Это подтверждение сотрудника, а не согласие родителя и не электронная подпись.</p>
    <p><Link className="text-link" href="/privacy-center">Документы и реестр целей</Link></p>
    {purposes.length ? <>
      <label>Правовое основание<select className="input" value={purpose} onChange={e => setPurpose(e.target.value)}><option value="">Выберите основание</option>{purposes.map(p => <option key={p.id} value={p.id}>{p.title} · {p.version}: {p.legal_basis}</option>)}</select></label>
      <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /> Я уполномочен и проверил наличие необходимых документов для выбранных пользователей.</label>
      <button type="button" className="button button-secondary" disabled={!purpose || !confirmed || !ids.length || busy} onClick={() => void save()}>Записать подтверждение документов</button>
    </> : <p>Утверждённые основания пока не настроены. Приглашения блокируются сервером до их настройки.</p>}
    {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
  </fieldset>;
}
