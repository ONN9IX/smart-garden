import { api } from "./client";

export type Operator = { name: string; address: string | null; contact: string | null; role: string | null; registration_details: string | null };
export type LegalDocument = { id: string; organization_id: string | null; document_type: string; version: string; title: string; operator: Operator; content: string; content_hash: string; effective_at: string };
export type Purpose = { id: string; code: string; version: string; title: string; document_id: string; consent_document_id: string | null; ready: boolean; consent_required: boolean | null; subject_categories: string[]; data_categories: string[]; operations: string[]; access_roles: string[]; legal_basis: string | null; retention: string | null; processors: string[] | null; locations: string[] | null };
export type PrivacyOverview = { organization_id: string; organization_name: string; operator_configured: boolean; documents: LegalDocument[]; purposes: Purpose[]; real_pii_pilot: "NO-GO" };
export type Subject = { label: string; subject_user_id: string | null; child_id: string | null; guardian_id: string | null };
export type PaperConsent = { id: string; purpose_id: string; purpose_title: string; subject_user_id: string | null; child_id: string | null; guardian_id: string | null; document_id: string; document_type: string; document_version: string; document_hash: string; document?: LegalDocument; received_on: string; recorded_by: string; status: "recorded" | "withdrawn"; current_version: boolean; history: { action: "recorded" | "withdrawn"; at: string; actor_user_id: string }[] };
export type RequestKind = "access" | "correction" | "withdrawal" | "stop_processing" | "erasure";
export type RequestStatus = "submitted" | "verifying" | "in_review" | "completed" | "declined";
export type PrivacyRequest = { id: string; requester_user_id: string; child_id: string | null; kind: RequestKind; status: RequestStatus; due_at: string | null; needs_deadline: boolean; overdue: boolean; created_at: string; history: { status: RequestStatus; at: string; decision_code: string | null }[] };
export const privacyApi = {
  public: (garden?: string) => api.get<{ documents: LegalDocument[] }>(garden ? `/privacy/public/gardens/${encodeURIComponent(garden)}` : "/privacy/public/provider"),
  me: () => api.get<PrivacyOverview>("/privacy/me"),
  subjects: () => api.get<Subject[]>("/privacy/subjects"),
  attest: (type: "guardian" | "employee", ids: string[], purposeId: string) => api.post<{ recorded: number; is_subject_consent: false }>("/privacy/attestations", { profile_type: type, profile_ids: ids, purpose_id: purposeId, documents_confirmed: true }),
  consents: () => api.get<PaperConsent[]>("/privacy/consents"),
  record: (input: { purpose_id: string; document_id: string; subject_user_id: string | null; child_id: string | null; guardian_id: string | null; received_on: string; idempotency_key: string }) => api.post<PaperConsent>("/privacy/consents", { ...input, original_held_confirmed: true, authority_confirmed: true }),
  withdraw: (id: string) => api.post<PaperConsent>(`/privacy/consents/${encodeURIComponent(id)}/withdraw`),
  requests: (queue = false) => api.get<PrivacyRequest[]>(queue ? "/privacy/operator/requests" : "/privacy/requests"),
  request: (kind: RequestKind, childId: string | null, key: string) => api.post<PrivacyRequest>("/privacy/requests", { kind, child_id: childId, idempotency_key: key }),
  transition: (id: string, payload: { status: RequestStatus; expected_status: RequestStatus; due_at?: string; outcome_confirmed?: boolean; decision_code?: string }) => api.post<PrivacyRequest>(`/privacy/operator/requests/${encodeURIComponent(id)}/status`, payload),
};
