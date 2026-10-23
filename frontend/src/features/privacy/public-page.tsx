"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/alert";
import { privacyApi, type LegalDocument } from "@/lib/api/privacy";
import { Documents } from "./documents";

export function PublicPrivacy({ garden }: { garden?: string }) {
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    let live = true;
    const sources = [privacyApi.public(), ...(garden ? [privacyApi.public(garden)] : [])];
    void Promise.all(sources).then(results => { if (live) setDocuments(results.flatMap(r => r.documents)); })
      .catch(() => { if (live) setError(true); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [garden]);
  return <main className="main-content" style={{ maxWidth: 900, margin: "auto" }}>
    <Link className="text-link" href="/login">Ко входу</Link><h1>Политика обработки персональных данных</h1>
    <Alert>Подготовительный режим: только синтетические данные. Реальный пилот не разрешён. Техническая реализация не означает юридического одобрения.</Alert>
    <p>Оператор организации и поставщик ПРОМАКС имеют отдельные юридические контексты. Их роли, реквизиты и основания должны быть подтверждены отдельно.</p>
    {!garden && <p>Документы вашей организации доступны по её публичной ссылке и в разделе «Конфиденциальность» после входа. Общая страница не заменяет уведомление конкретного оператора.</p>}
    {loading ? <p>Загрузка документов…</p> : error ? <Alert>Не удалось загрузить документы. Попробуйте открыть страницу снова.</Alert> : <Documents documents={documents} />}
    <p>Доступ к кабинету использует техническую cookie сессии. Вход, восстановление пароля и просмотр документов не создают согласия на обработку. Бумажные оригиналы согласий остаются у оператора; загружать сканы, паспорта и подписи в ПРОМАКС нельзя.</p>
  </main>;
}
