export type ManagementAttentionItem = {
  kind: string;
  entity_type: string | null;
  entity_id: string | null;
  count: number | null;
};

export type ManagementTodayGroup = {
  group_id: string;
  group_name: string;
  active_children: number;
  present: number;
  on_site: number;
  departed: number;
  absent: number;
  unknown: number;
  needs_arrival: number;
  has_active_teacher: boolean;
  has_active_weekly_schedule: boolean;
};

export type ManagementToday = {
  date: string;
  active_children: number;
  present: number;
  on_site: number;
  departed: number;
  absent: number;
  unknown: number;
  needs_arrival: number;
  active_groups: number;
  active_employees: number;
  groups_without_active_teacher_assignment: number;
  open_tasks: number;
  overdue_tasks: number;
  open_incidents: number;
  unread_notifications: number;
  groups: ManagementTodayGroup[];
  attention_items: ManagementAttentionItem[];
};

export type TeacherAccountView = {
  user_id: string;
  username: string;
  status: "active" | "blocked";
  must_change_password: boolean;
};

export type TeacherAssignmentView = {
  id: string;
  group_id: string;
  group_name: string;
  status: "active" | "archived";
};

export type TeacherProjection = {
  employee_id: string;
  first_name: string;
  last_name: string;
  middle_name: string | null;
  position: string;
  employee_status: "active" | "archived";
  account: TeacherAccountView | null;
  assignments: TeacherAssignmentView[];
  eligible_for_teacher_account: boolean;
};

export type TeacherProjectionList = { items: TeacherProjection[] };

export type TemporaryTeacherCredentials = {
  username: string;
  role: "TEACHER";
  status: "pending" | "sent" | "failed";
};

export type FoundationAssignment = {
  id: string;
  employee_id: string;
  group_id: string;
  status: "active" | "archived";
  assigned_by: string;
  created_at: string;
  archived_at: string | null;
};

export type ScheduleItem = {
  id: string;
  group_id: string;
  weekday: number;
  start_time: string;
  end_time: string;
  title: string;
  status: "active" | "archived";
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
};

export type ManagementMessage = {
  id: string;
  thread_id: string;
  group_id: string;
  sender_user_id: string;
  sender_role: "DIRECTOR" | "ADMIN" | "TEACHER" | "PARENT";
  sender_name: string;
  audience: "all" | "parents" | "teachers";
  body: string;
  created_at: string;
};

export type DiaryEntry = {
  id: string;
  child_id: string;
  group_id: string;
  date: string;
  author_user_id: string;
  note: string;
  created_at: string;
  updated_at: string;
};

export type PollOptionResult = {
  id: string;
  label: string;
  sort_order: number;
  vote_count: number;
};

export type ManagementPoll = {
  id: string;
  group_id: string;
  question: string;
  status: "active" | "closed" | "archived";
  closes_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  options: PollOptionResult[];
  total_votes: number;
};

export type Incident = {
  id: string;
  group_id: string;
  child_id: string | null;
  occurred_at: string;
  category: "safety" | "behavior" | "operational" | "other";
  description: string;
  status: "open" | "resolved";
  reported_by: string;
  resolved_by: string | null;
  created_at: string;
  updated_at: string;
};

export type TeacherTask = {
  id: string;
  assignee_employee_id: string;
  group_id: string | null;
  title: string;
  description: string | null;
  due_at: string | null;
  status: "open" | "in_progress" | "done" | "cancelled";
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type ManagementNotification = {
  id: string;
  kind: string;
  entity_type: string;
  entity_id: string | null;
  read_at: string | null;
  created_at: string;
};

export type DocumentNotice = {
  id: string;
  recipient_user_id: string;
  title: string;
  kind: string;
  requires_ack: boolean;
  issued_by: string;
  acknowledged_at: string | null;
  created_at: string;
};

export type PhotoConsent = {
  id: string;
  child_id: string;
  status: "granted" | "withdrawn";
  scope: "group_photo_report";
  effective_from: string;
  effective_to: string | null;
  recorded_by: string;
  created_at: string;
  updated_at: string;
};

export type ManagementSettings = {
  id: string;
  name: string;
  timezone: string;
};
