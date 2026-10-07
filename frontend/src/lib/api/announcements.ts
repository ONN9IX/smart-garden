/** Announcement free text stays in request memory and is never placed in URLs or browser storage. */
import { api } from "./client";
import type {
  Announcement,
  AnnouncementFields,
  AnnouncementStatusFilter,
  AnnouncementTarget,
} from "@/types/stage4";

export const announcementsApi = {
  list(status: AnnouncementStatusFilter, targetType?: AnnouncementTarget, groupId?: string) {
    const query = new URLSearchParams({ status });
    if (targetType) query.set("target_type", targetType);
    if (groupId) query.set("group_id", groupId);
    return api.get<{ items: Announcement[] }>(`/announcements?${query.toString()}`);
  },
  get: (id: string) => api.get<Announcement>(`/announcements/${encodeURIComponent(id)}`),
  create: (fields: AnnouncementFields, idempotencyKey: string) => api.post<Announcement>(
    "/announcements", fields, { "Idempotency-Key": idempotencyKey },
  ),
  update: (id: string, fields: Partial<AnnouncementFields>) => (
    api.patch<Announcement>(`/announcements/${encodeURIComponent(id)}`, fields)
  ),
  archive: (id: string) => api.post<Announcement>(`/announcements/${encodeURIComponent(id)}/archive`),
};
