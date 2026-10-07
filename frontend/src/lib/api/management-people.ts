import { api } from "./client";
import type { Child } from "@/types/stage2";
import type { DuplicateMatch, DuplicateRequest, EmployeeProfile, FamilyCreateInput, GroupOverview, GroupProfile, GuardianSearchMatch } from "@/types/people";

export const managementPeopleApi = {
  checkDuplicates: (request: DuplicateRequest) => api.post<{ matches: DuplicateMatch[] }>("/management/people/duplicates", request),
  searchGuardians: (query: string) => api.post<{ matches: GuardianSearchMatch[] }>("/management/people/guardian-search", { query }),
  createFamily: (request: FamilyCreateInput) => api.post<Child>("/management/families", request),
  groupProfile: (id: string) => api.get<GroupProfile>(`/management/groups/${encodeURIComponent(id)}/profile`),
  groupOverviews: (status: "active" | "archived" | "all" = "active") => api.get<{ items: GroupOverview[] }>(`/management/groups/overview?status=${status}`),
  employeeProfile: (id: string) => api.get<EmployeeProfile>(`/management/employees/${encodeURIComponent(id)}/profile`),
};
