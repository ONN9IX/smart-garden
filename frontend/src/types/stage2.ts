/**
 * Stage 2 transport objects; fields and nesting match docs/15-api-contract-stage-2.md.
 * Personal data remains in memory only while the relevant screen is mounted.
 */
export type RecordStatus = "active" | "archived";
export type StatusFilter = RecordStatus | "all";
export type RelationType = "mother" | "father" | "legal_guardian" | "other";

export interface Group {
  id: string;
  name: string;
  status: RecordStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface GroupSummary {
  id: string;
  name: string;
  status: RecordStatus;
}

export interface GuardianSummary {
  id: string;
  first_name: string;
  last_name: string;
  middle_name: string | null;
  phone: string | null;
  email: string | null;
  status: RecordStatus;
}

export interface ChildSummary {
  id: string;
  first_name: string;
  last_name: string;
  middle_name: string | null;
  birth_date: string;
  status: RecordStatus;
  group: GroupSummary;
}

export interface ChildGuardian {
  id: string;
  relation_type: RelationType;
  status: RecordStatus;
  guardian: GuardianSummary;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Child extends ChildSummary {
  guardians: ChildGuardian[];
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ParentAccountSummary {
  id: string;
  username: string;
  status: "active" | "blocked";
  must_change_password: boolean;
}

export interface GuardianChildRelation {
  relation_id: string;
  relation_type: RelationType;
  relation_status: RecordStatus;
  child: ChildSummary;
}

export interface Guardian extends GuardianSummary {
  children: GuardianChildRelation[];
  account: ParentAccountSummary | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface GuardianListItem extends GuardianSummary {
  account: ParentAccountSummary | null;
}

export interface TemporaryCredentials {
  account: ParentAccountSummary;
  temporary_password: string;
}

export interface ListResponse<T> { items: T[] }

export interface ChildFields {
  group_id: string;
  first_name: string;
  last_name: string;
  middle_name: string | null;
  birth_date: string;
}

export interface GuardianFields {
  first_name: string;
  last_name: string;
  middle_name: string | null;
  phone: string | null;
  email: string | null;
}

export const RELATION_LABELS: Record<RelationType, string> = {
  mother: "Мать",
  father: "Отец",
  legal_guardian: "Законный представитель",
  other: "Другой представитель",
};
