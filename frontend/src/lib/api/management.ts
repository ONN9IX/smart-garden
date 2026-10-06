import { api } from "./client";
import type {
  DiaryEntry,
  DocumentNotice,
  FoundationAssignment,
  Incident,
  ManagementMessage,
  ManagementNotification,
  ManagementPoll,
  ManagementSettings,
  ManagementToday,
  PhotoConsent,
  ScheduleItem,
  TeacherProjection,
  TeacherProjectionList,
  TeacherTask,
  TemporaryTeacherCredentials,
} from "@/types/management";

const query = (values: Record<string, string | undefined>) => {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); });
  const rendered = params.toString();
  return rendered ? `?${rendered}` : "";
};

type TeacherAccount = TemporaryTeacherCredentials["account"];

export const managementApi = {
  today: () => api.get<ManagementToday>("/management/today"),

  teachers: (filters: { status?: string; account_status?: string; group_id?: string; q?: string } = {}) =>
    api.get<TeacherProjectionList>(`/teacher-management/teachers${query(filters)}`),
  teacher: (employeeId: string) =>
    api.get<TeacherProjection>(`/teacher-management/teachers/${encodeURIComponent(employeeId)}`),
  createTeacherAccount: (employeeId: string) =>
    api.post<TemporaryTeacherCredentials>(`/teacher-management/employees/${encodeURIComponent(employeeId)}/account`),
  resetTeacherPassword: (employeeId: string) =>
    api.post<TemporaryTeacherCredentials>(`/teacher-management/employees/${encodeURIComponent(employeeId)}/account/reset-password`),
  blockTeacher: (employeeId: string) =>
    api.post<TeacherAccount>(`/teacher-management/employees/${encodeURIComponent(employeeId)}/account/block`),
  unblockTeacher: (employeeId: string) =>
    api.post<TeacherAccount>(`/teacher-management/employees/${encodeURIComponent(employeeId)}/account/unblock`),

  assignments: () => api.get<{ items: FoundationAssignment[] }>("/teacher-management/assignments"),
  createAssignment: (employeeId: string, groupId: string) =>
    api.post<FoundationAssignment>("/teacher-management/assignments", {
      employee_id: employeeId,
      group_id: groupId,
    }),
  archiveAssignment: (assignmentId: string) =>
    api.post<FoundationAssignment>(`/teacher-management/assignments/${encodeURIComponent(assignmentId)}/archive`),
  restoreAssignment: (assignmentId: string) =>
    api.post<FoundationAssignment>(`/teacher-management/assignments/${encodeURIComponent(assignmentId)}/restore`),

  schedule: (groupId?: string, status = "active") =>
    api.get<{ items: ScheduleItem[] }>(`/teacher-management/schedule${query({ group_id: groupId, status })}`),
  createSchedule: (body: { group_id: string; weekday: number; start_time: string; end_time: string; title: string }) =>
    api.post<ScheduleItem>("/teacher-management/schedule", body),
  updateSchedule: (id: string, body: Partial<{ group_id: string; weekday: number; start_time: string; end_time: string; title: string }>) =>
    api.patch<ScheduleItem>(`/teacher-management/schedule/${encodeURIComponent(id)}`, body),
  archiveSchedule: (id: string) =>
    api.post<ScheduleItem>(`/teacher-management/schedule/${encodeURIComponent(id)}/archive`),

  groupMessages: (groupId: string, audience: "all" | "parents" | "teachers" = "all") =>
    api.get<{ items: ManagementMessage[] }>(`/teacher-management/communications/groups/${encodeURIComponent(groupId)}/messages?audience=${audience}`),
  sendGroupMessage: (groupId: string, body: string, audience: "all" | "parents" | "teachers" = "all") =>
    api.post<ManagementMessage>(`/teacher-management/communications/groups/${encodeURIComponent(groupId)}/messages`, { body, audience }),

  diary: (childId: string, dateFrom?: string, dateTo?: string) =>
    api.get<{ items: DiaryEntry[] }>(`/teacher-management/diary${query({ child_id: childId, date_from: dateFrom, date_to: dateTo })}`),
  diaryEntry: (id: string) => api.get<DiaryEntry>(`/teacher-management/diary/${encodeURIComponent(id)}`),

  polls: (groupId?: string, status = "all") =>
    api.get<{ items: ManagementPoll[] }>(`/teacher-management/polls${query({ group_id: groupId, status })}`),
  poll: (id: string) => api.get<ManagementPoll>(`/teacher-management/polls/${encodeURIComponent(id)}`),
  createPoll: (body: { group_id: string; question: string; options: string[]; closes_at?: string | null }) =>
    api.post<ManagementPoll>("/teacher-management/polls", body),
  closePoll: (id: string) => api.post<ManagementPoll>(`/teacher-management/polls/${encodeURIComponent(id)}/close`),

  incidents: (groupId?: string, status = "all") =>
    api.get<{ items: Incident[] }>(`/teacher-management/incidents${query({ group_id: groupId, status })}`),
  createIncident: (body: {
    group_id: string;
    child_id?: string | null;
    occurred_at: string;
    category: Incident["category"];
    description: string;
  }) => api.post<Incident>("/teacher-management/incidents", body),
  updateIncident: (id: string, body: Partial<Pick<Incident, "occurred_at" | "category" | "description" | "status">>) =>
    api.patch<Incident>(`/teacher-management/incidents/${encodeURIComponent(id)}`, body),

  tasks: (filters: { employee_id?: string; group_id?: string; status?: string } = {}) =>
    api.get<{ items: TeacherTask[] }>(`/teacher-management/tasks${query(filters)}`),
  createTask: (body: {
    assignee_employee_id: string;
    group_id?: string | null;
    title: string;
    description?: string | null;
    due_at?: string | null;
  }) => api.post<TeacherTask>("/teacher-management/tasks", body),
  updateTask: (id: string, body: Partial<{
    assignee_employee_id: string;
    group_id: string | null;
    title: string;
    description: string | null;
    due_at: string | null;
    status: "open" | "in_progress" | "done";
  }>) => api.patch<TeacherTask>(`/teacher-management/tasks/${encodeURIComponent(id)}`, body),
  cancelTask: (id: string) => api.post<TeacherTask>(`/teacher-management/tasks/${encodeURIComponent(id)}/cancel`),

  notifications: (status = "unread") =>
    api.get<{ items: ManagementNotification[] }>(`/management/notifications${query({ status })}`),
  readNotification: (id: string) =>
    api.post<ManagementNotification>(`/management/notifications/${encodeURIComponent(id)}/read`),

  documentNotices: (recipientUserId?: string) =>
    api.get<{ items: DocumentNotice[] }>(`/teacher-management/document-notices${query({ recipient_user_id: recipientUserId })}`),
  createDocumentNotice: (body: { recipient_user_id: string; title: string; kind: string; requires_ack: boolean }) =>
    api.post<DocumentNotice>("/teacher-management/document-notices", body),

  photoConsents: (filters: { child_id?: string; group_id?: string } = {}) =>
    api.get<{ items: PhotoConsent[] }>(`/teacher-management/photo-consents${query(filters)}`),
  recordPhotoConsent: (body: { child_id: string; effective_from: string; effective_to?: string | null }) =>
    api.post<PhotoConsent>("/teacher-management/photo-consents", body),
  withdrawPhotoConsent: (id: string) =>
    api.post<PhotoConsent>(`/teacher-management/photo-consents/${encodeURIComponent(id)}/withdraw`),

  settings: () => api.get<ManagementSettings>("/management/settings"),
  updateSettings: (body: Partial<Pick<ManagementSettings, "name" | "timezone">>) =>
    api.patch<ManagementSettings>("/management/settings", body),
};
