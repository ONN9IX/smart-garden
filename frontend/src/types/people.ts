import type { EmployeeCategory } from "@/types/stage3";
import type { Group, RelationType, RecordStatus } from "@/types/stage2";

export type DuplicateKind = "child" | "guardian" | "employee";
export type DuplicateMatch = { id: string; full_name: string; context: string | null };
export type DuplicateRequest = {
  kind: DuplicateKind;
  first_name: string;
  last_name: string;
  middle_name?: string | null;
  birth_date?: string | null;
  phone?: string | null;
  email?: string | null;
};
export type FamilyGuardianInput =
  | { guardian_id: string; relation_type: RelationType }
  | { new_guardian: { first_name: string; last_name: string; middle_name: string | null; phone: string | null; email: string | null }; relation_type: RelationType };
export type FamilyCreateInput = {
  child: { group_id: string; first_name: string; last_name: string; middle_name: string | null; birth_date: string };
  guardians: FamilyGuardianInput[];
};
export type GuardianSearchMatch = { id: string; full_name: string; phone: string | null; email: string | null; account_status: "active" | "blocked" | null };

export type GroupProfile = {
  group: Group;
  local_date: string;
  active_children: number;
  present: number;
  absent: number;
  unknown: number;
  active_teacher_count: number;
  parent_count: number;
  active_schedule_count: number;
  open_tasks: number;
  overdue_tasks: number;
  children: Array<{
    id: string; first_name: string; last_name: string; middle_name: string | null;
    status: RecordStatus; today_attendance: "present" | "absent" | "unknown" | null;
    active_guardian_count: number;
  }>;
  employees: Array<{
    id: string; first_name: string; last_name: string; middle_name: string | null;
    position: string; category: EmployeeCategory; account_status: "active" | "blocked" | null;
  }>;
  parents: Array<{
    id: string; first_name: string; last_name: string; middle_name: string | null;
    phone: string | null; email: string | null; account_status: "active" | "blocked" | null;
    child_id: string; child_name: string; relation_type: RelationType;
  }>;
  schedule: Array<{ id: string; weekday: number; start_time: string; end_time: string; title: string }>;
};

export type GroupOverview = {
  group: Group;
  active_children: number;
  present: number;
  absent: number;
  unknown: number;
  active_teacher_names: string[];
  has_active_weekly_schedule: boolean;
  open_tasks: number;
  overdue_tasks: number;
};

export type EmployeeProfile = {
  employee_id: string;
  assignments: Array<{ group_id: string; group_name: string; status: RecordStatus; archived_at: string | null }>;
  open_tasks: number;
  overdue_tasks: number;
};
