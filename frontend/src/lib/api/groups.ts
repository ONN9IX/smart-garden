/** Tenant is inferred from the server session; callers never send organization_id. */
import { api } from "./client";
import type { Group, ListResponse, StatusFilter } from "@/types/stage2";

export const groupsApi = {
  list: (status: StatusFilter = "active") => api.get<ListResponse<Group>>(`/groups?status=${status}`),
  get: (id: string) => api.get<Group>(`/groups/${encodeURIComponent(id)}`),
  create: (name: string) => api.post<Group>("/groups", { name }),
  update: (id: string, name: string) => api.patch<Group>(`/groups/${encodeURIComponent(id)}`, { name }),
  archive: (id: string) => api.post<Group>(`/groups/${encodeURIComponent(id)}/archive`),
  restore: (id: string) => api.post<Group>(`/groups/${encodeURIComponent(id)}/restore`),
};
