/** Guardian and parent lifecycle calls. Temporary credentials are returned once. */
import { api } from "./client";
import type { Guardian, GuardianFields, GuardianListItem, ListResponse, ParentAccountSummary, StatusFilter, TemporaryCredentials } from "@/types/stage2";

export const guardiansApi = {
  list: ({ status = "active", q }: { status?: StatusFilter; q?: string } = {}) => {
    const query = new URLSearchParams({ status });
    if (q) query.set("q", q);
    return api.get<ListResponse<GuardianListItem>>(`/guardians?${query}`);
  },
  get: (id: string) => api.get<Guardian>(`/guardians/${encodeURIComponent(id)}`),
  create: (fields: GuardianFields) => api.post<Guardian>("/guardians", fields),
  update: (id: string, fields: Partial<GuardianFields>) => api.patch<Guardian>(`/guardians/${encodeURIComponent(id)}`, fields),
  archive: (id: string) => api.post<Guardian>(`/guardians/${encodeURIComponent(id)}/archive`),
  restore: (id: string) => api.post<Guardian>(`/guardians/${encodeURIComponent(id)}/restore`),
  createAccount: (id: string) => api.post<TemporaryCredentials>(`/guardians/${encodeURIComponent(id)}/account`),
  resetPassword: (id: string) => api.post<TemporaryCredentials>(`/guardians/${encodeURIComponent(id)}/account/reset-password`),
  blockAccount: (id: string) => api.post<ParentAccountSummary>(`/guardians/${encodeURIComponent(id)}/account/block`),
  unblockAccount: (id: string) => api.post<ParentAccountSummary>(`/guardians/${encodeURIComponent(id)}/account/unblock`),
};
