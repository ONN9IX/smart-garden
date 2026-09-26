import { api } from "./client";
import type { AttendanceDetail, AttendanceRow, AttendanceStatus } from "@/types/stage3";

export const attendanceApi = {
  list: (date: string, groupId?: string, status?: AttendanceStatus | "all", childId?: string) => {
    const query = new URLSearchParams({ date });
    if (groupId) query.set("group_id", groupId);
    if (status && status !== "all") query.set("status", status);
    if (childId) query.set("child_id", childId);
    return api.get<{ items: AttendanceRow[] }>(`/attendance?${query}`);
  },
  save: (body: { child_id: string; date: string; status: AttendanceStatus; arrival_time: string | null; departure_time: string | null }) => api.post<AttendanceDetail>("/attendance", body),
  get: (id: string) => api.get<AttendanceDetail>(`/attendance/${encodeURIComponent(id)}`),
  patch: (id: string, body: Partial<Pick<AttendanceDetail, "status" | "arrival_time" | "departure_time">>) => api.patch<AttendanceDetail>(`/attendance/${encodeURIComponent(id)}`, body),
};
