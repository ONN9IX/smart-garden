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

export type AnnouncementTarget = "all" | "group";
export type AnnouncementStatus = "active" | "archived";
export type AnnouncementStatusFilter = AnnouncementStatus | "all";

export type Announcement = {
  id: string;
  target_type: AnnouncementTarget;
  group: { id: string; name: string } | null;
  title: string;
  body: string;
  status: AnnouncementStatus;
  created_by: string;
  updated_by: string;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AnnouncementFields = {
  target_type: AnnouncementTarget;
  group_id: string | null;
  title: string;
  body: string;
};

export type DashboardGroup = {
  id: string;
  name: string;
  active_children: number;
  present: number;
  absent: number;
  unknown: number;
};

export type DashboardSummary = {
  date: string;
  active_children: number;
  present: number;
  absent: number;
  unknown: number;
  active_groups: number;
  active_employees: number;
  groups: DashboardGroup[];
};
