import Link from "next/link";
import type { LegalDocument } from "@/lib/api/privacy";

export function PrivacyLink() {
  return <p className="muted"><Link className="text-link" href="/privacy">Политика обработки персональных данных</Link>. Для входа используется техническая cookie сессии. Вход и просмотр политики не означают согласия на дополнительные цели.</p>;
}

export function Documents({ documents }: { documents: LegalDocument[] }) {
  if (!documents.length) return <p role="status">Утверждённые действующие документы ещё не опубликованы. Реквизиты, основания и контакты должны быть подтверждены до работы с реальными данными.</p>;
  return <>{documents.map(doc => <article className="card section-card section-space" key={doc.id}>
    <p className="eyebrow">{doc.organization_id ? "Оператор организации" : "Поставщик ПРОМАКС — собственная обработка"}</p>
    <h2>{doc.title}</h2><p>Версия {doc.version} · действует с {new Date(doc.effective_at).toLocaleDateString("ru-RU")}</p>
    <p><strong>{doc.operator.name}</strong><br />{doc.operator.role}<br />{doc.operator.address}<br />{doc.operator.registration_details}<br />Обращения: {doc.operator.contact}</p>
    <div style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{doc.content}</div>
    <details><summary>Контрольная сумма документа</summary><p style={{ overflowWrap: "anywhere" }}>SHA-256: {doc.content_hash}</p></details>
  </article>)}</>;
}
