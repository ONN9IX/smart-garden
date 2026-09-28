import { api } from "./client";
import type { AuditFilters, AuditList } from "@/types/stage4";

export const auditApi = {
  list(filters: AuditFilters) {
    const query = new URLSearchParams();
    if (filters.entity_type) query.set("entity_type", filters.entity_type);
    if (filters.action) query.set("action", filters.action);
    if (filters.date_from) query.set("date_from", filters.date_from);
    if (filters.date_to) query.set("date_to", filters.date_to);
    query.set("limit", String(filters.limit));
    query.set("offset", String(filters.offset));
    return api.get<AuditList>(`/audit?${query.toString()}`);
  },
};
