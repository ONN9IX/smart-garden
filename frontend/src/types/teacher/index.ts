export type GroupSummary = { id: string; name: string };
export type ChildSummary = { id: string; first_name: string; last_name: string; middle_name: string | null };
export type GuardianContext = ChildSummary & {
  child_id: string; relation_type: "mother" | "father" | "legal_guardian" | "other";
  phone: string | null; email: string | null;
};
export type ScheduleItem = {
  id: string; group_id: string; weekday: number; start_time: string; end_time: string; title: string;
};
export type AttendanceRow = {
  record_id: string | null; date: string; child: ChildSummary & { status: "active" | "archived" };
  group: GroupSummary; status: "present" | "absent" | "unknown";
  arrival_time: string | null; departure_time: string | null;
};
export type Thread = {
  id: string; thread_type: "group" | "direct"; group_id: string;
  child_id: string | null; guardian_id: string | null; created_at: string;
};
export type Message = { id: string; thread_id: string; sender_user_id: string; body: string; created_at: string };
export type DiaryEntry = {
  id: string; child_id: string; group_id: string; date: string; author_user_id: string;
  note: string; created_at: string; updated_at: string;
};
export type Announcement = {
  id: string; target_type: "all" | "group"; group_id: string | null; title: string; body: string;
  status: "active" | "archived"; created_by: string; created_at: string; updated_at: string;
};
export type Poll = {
  id: string; group_id: string; question: string; status: "active" | "closed" | "archived";
  closes_at: string | null; created_by: string; created_at: string; selected_option_id: string | null;
  options: { id: string; label: string; sort_order: number }[];
};
export type Incident = {
  id: string; group_id: string; child_id: string | null; occurred_at: string;
  category: "safety" | "behavior" | "operational" | "other"; description: string;
  status: "open" | "resolved"; reported_by: string; resolved_by: string | null;
  created_at: string; updated_at: string;
};
export type TeacherTask = {
  id: string; group_id: string | null; title: string; description: string | null; due_at: string | null;
  status: "open" | "in_progress" | "done" | "cancelled"; created_at: string; updated_at: string;
};
export type Notification = {
  id: string; kind: string; entity_type: string; entity_id: string | null; read_at: string | null; created_at: string;
};
export type DocumentNotice = {
  id: string; title: string; kind: string; requires_ack: boolean; acknowledged_at: string | null; created_at: string;
};
export type PhotoConsent = {
  id: string; child_id: string; status: "granted" | "withdrawn"; scope: "group_photo_report";
  effective_from: string; effective_to: string | null;
};
export type PhotoAsset = {
  id: string; group_id: string; child_ids: string[]; mime_type: string; size_bytes: number;
  captured_at: string | null; status: "active" | "restricted" | "removed"; created_at: string;
};
export type Today = {
  date: string; groups: GroupSummary[]; schedule: ScheduleItem[];
  attendance: { group_id: string; present: number; absent: number; unknown: number }[];
  tasks: TeacherTask[]; notifications: Notification[]; unread_communication_count: number;
};
