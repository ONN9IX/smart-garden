/** Child and relation calls; all IDs are opaque UUIDs validated by the backend. */
import { api } from "./client";
import type { Child, ChildFields, ChildGuardian, ChildSummary, ListResponse, RelationType, StatusFilter } from "@/types/stage2";

export const childrenApi = {
  list: ({ status = "active", groupId, q }: { status?: StatusFilter; groupId?: string; q?: string } = {}) => {
    const query = new URLSearchParams({ status });
    if (groupId) query.set("group_id", groupId);
    if (q) query.set("q", q);
    return api.get<ListResponse<ChildSummary>>(`/children?${query}`);
  },
  get: (id: string) => api.get<Child>(`/children/${encodeURIComponent(id)}`),
  create: (fields: ChildFields) => api.post<Child>("/children", fields),
  update: (id: string, fields: Partial<ChildFields>) => api.patch<Child>(`/children/${encodeURIComponent(id)}`, fields),
  archive: (id: string) => api.post<Child>(`/children/${encodeURIComponent(id)}/archive`),
  restore: (id: string) => api.post<Child>(`/children/${encodeURIComponent(id)}/restore`),
  link: (childId: string, guardianId: string, relationType: RelationType) =>
    api.post<ChildGuardian>(`/children/${encodeURIComponent(childId)}/guardians`, { guardian_id: guardianId, relation_type: relationType }),
  updateLink: (childId: string, guardianId: string, relationType: RelationType) =>
    api.patch<ChildGuardian>(`/children/${encodeURIComponent(childId)}/guardians/${encodeURIComponent(guardianId)}`, { relation_type: relationType }),
  archiveLink: (childId: string, guardianId: string) =>
    api.post<ChildGuardian>(`/children/${encodeURIComponent(childId)}/guardians/${encodeURIComponent(guardianId)}/archive`),
  restoreLink: (childId: string, guardianId: string) =>
    api.post<ChildGuardian>(`/children/${encodeURIComponent(childId)}/guardians/${encodeURIComponent(guardianId)}/restore`),
};
