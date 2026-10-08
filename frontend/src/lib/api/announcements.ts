/** Announcement free text stays in request memory and is never placed in URLs or browser storage. */
import { api } from "./client";
import type {
  Announcement,
  AnnouncementFields,
  AnnouncementStatusFilter,
  AnnouncementTarget,
  CommunicationsAnnouncement,
  CommunicationsAnnouncementFields,
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

export const communicationsAnnouncementsApi = {
  preview(fields: Pick<CommunicationsAnnouncementFields, "target_type" | "group_id" | "audience">) {
    return api.post<{ recipient_count: number; parents_count: number; staff_count: number }>("/communications/v2/announcements/preview", fields);
  },
  list(status: AnnouncementStatusFilter) {
    return api.get<CommunicationsAnnouncement[]>(`/communications/v2/announcements?status=${status}`);
  },
  get: (id: string) => api.get<CommunicationsAnnouncement>(`/communications/v2/announcements/${encodeURIComponent(id)}`),
  create: (fields: CommunicationsAnnouncementFields, idempotencyKey: string) => api.post<CommunicationsAnnouncement>(
    "/communications/v2/announcements", fields, { "Idempotency-Key": idempotencyKey },
  ),
  update: (id: string, fields: Pick<CommunicationsAnnouncementFields, "title" | "body">) => (
    api.patch<CommunicationsAnnouncement>(`/communications/v2/announcements/${encodeURIComponent(id)}`, fields)
  ),
  archive: (id: string) => api.post<CommunicationsAnnouncement>(`/communications/v2/announcements/${encodeURIComponent(id)}/archive`),
};
