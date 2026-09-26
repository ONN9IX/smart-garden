import { api } from "./client";
import type { Employee, EmployeeFields, EmployeeSummary, TemporaryCredentials, EmployeeAccount } from "@/types/stage3";

const path = (id: string) => `/employees/${encodeURIComponent(id)}`;
export const employeesApi = {
  list: (status: "active" | "archived" | "all" = "active") => api.get<{ items: EmployeeSummary[] }>(`/employees?status=${status}`),
  get: (id: string) => api.get<Employee>(path(id)),
  create: (fields: EmployeeFields) => api.post<Employee>("/employees", fields),
  update: (id: string, fields: Partial<EmployeeFields>) => api.patch<Employee>(path(id), fields),
  archive: (id: string) => api.post<Employee>(`${path(id)}/archive`),
  restore: (id: string) => api.post<Employee>(`${path(id)}/restore`),
  createAccount: (id: string) => api.post<TemporaryCredentials>(`${path(id)}/account`),
  resetPassword: (id: string) => api.post<TemporaryCredentials>(`${path(id)}/account/reset-password`),
  block: (id: string) => api.post<EmployeeAccount>(`${path(id)}/account/block`),
  unblock: (id: string) => api.post<EmployeeAccount>(`${path(id)}/account/unblock`),
};
