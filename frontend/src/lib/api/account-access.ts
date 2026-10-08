import { api } from "./client";

export type AccessStatus = "no_account" | "invited" | "delivery_failed" | "invite_expired" | "activated" | "blocked";
export interface AccessItem { profile_id: string; profile_type: "guardian" | "employee"; full_name: string; context: string; username: string | null; role: "PARENT" | "TEACHER" | "ADMIN" | null; masked_email: string | null; status: AccessStatus; last_login_at: string | null; groups: string[]; }
export interface AccessSections { parents: AccessItem[]; teachers: AccessItem[]; administrators: AccessItem[]; other_employees: AccessItem[]; blocked: AccessItem[]; }
export interface BulkResponse { preflight: Record<"eligible" | "missing_or_invalid_email" | "activated" | "already_invited" | "failed_or_expired" | "blocked" | "archived" | "no_active_linked_child", number>; results: Array<{ guardian_id: string; result: "sent" | "failed" | "skipped"; reason: string | null }>; }
export const accountAccessApi = {
  list: () => api.get<AccessSections>("/access-accounts"),
  bulkParents: (guardianIds: string[], confirm: boolean) => api.post<BulkResponse>("/access-accounts/parents/bulk-invite", { guardian_ids: guardianIds, confirm }),
  revokeSessions: (profileType: "guardian" | "employee", profileId: string) => api.post<{ success: true }>("/access-accounts/revoke-sessions", { profile_type: profileType, profile_id: profileId }),
};
