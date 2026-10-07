import { api } from "./client";
import type { Employee, EmployeeFields, EmployeeSummary, InvitationResult, EmployeeAccount } from "@/types/stage3";

const path = (id: string) => `/employees/${encodeURIComponent(id)}`;
export const employeesApi = {
  list: ({ status = "active", category, q }: { status?: "active" | "archived" | "all"; category?: "teacher" | "administrator" | "other"; q?: string } = {}) => {
    const query = new URLSearchParams({ status });
    if (category) query.set("category", category);
    if (q) query.set("q", q);
    return api.get<{ items: EmployeeSummary[] }>(`/employees?${query}`);
  },
  get: (id: string) => api.get<Employee>(path(id)),
  create: (fields: EmployeeFields) => api.post<Employee>("/employees", fields),
  update: (id: string, fields: Partial<EmployeeFields>) => api.patch<Employee>(path(id), fields),
  archive: (id: string) => api.post<Employee>(`${path(id)}/archive`),
  restore: (id: string) => api.post<Employee>(`${path(id)}/restore`),
  createAccount: (id: string, role: "TEACHER" | "ADMIN") => api.post<InvitationResult>(`${path(id)}/account`, { role }),
  resendInvite: (id: string, role: "TEACHER" | "ADMIN") => api.post<InvitationResult>(`${path(id)}/account/resend`, { role }),
  changeRole: (id: string, role: "TEACHER" | "ADMIN") => api.post<{ success: true }>(`${path(id)}/account/role`, { role }),
  block: (id: string) => api.post<EmployeeAccount>(`${path(id)}/account/block`),
  unblock: (id: string) => api.post<EmployeeAccount>(`${path(id)}/account/unblock`),
  createTeacherAccount: (id: string) => api.post<InvitationResult>(`/teacher-management/employees/${encodeURIComponent(id)}/account`),
  resendTeacherInvite: (id: string) => api.post<InvitationResult>(`/teacher-management/employees/${encodeURIComponent(id)}/account/resend`),
  blockTeacherAccount: (id: string) => api.post<EmployeeAccount>(`/teacher-management/employees/${encodeURIComponent(id)}/account/block`),
  unblockTeacherAccount: (id: string) => api.post<EmployeeAccount>(`/teacher-management/employees/${encodeURIComponent(id)}/account/unblock`),
};
