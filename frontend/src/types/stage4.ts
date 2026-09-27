export type AuditActor = {
  id: string;
  username: string;
  role: "DIRECTOR" | "ADMIN" | "PARENT";
};

export type AuditEvent = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor: AuditActor;
  details: Record<string, unknown>;
  created_at: string;
};

export type AuditList = { items: AuditEvent[]; limit: number; offset: number };

export type AuditFilters = {
  entity_type?: string;
  action?: string;
  date_from?: string;
  date_to?: string;
  limit: number;
  offset: number;
};
