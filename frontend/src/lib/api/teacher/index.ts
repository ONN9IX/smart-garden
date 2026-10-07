import { api, ApiError, NetworkError } from "@/lib/api/client";
import type {
  Announcement, AttendanceRow, ChildSummary, DiaryEntry, DocumentNotice, GroupSummary,
  GuardianContext, Incident, Message, Notification, ParentToday, PhotoAsset, PhotoConsent, Poll,
  ScheduleItem, TeacherTask, Thread, Today,
} from "@/types/teacher";

const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

export const teacherApi = {
  today: () => api.get<Today>("/teacher/today"),
  groups: () => api.get<GroupSummary[]>("/teacher/groups"),
  children: (groupId: string) => api.get<ChildSummary[]>(`/teacher/groups/${groupId}/children`),
  guardians: (groupId: string) => api.get<GuardianContext[]>(`/teacher/groups/${groupId}/guardians`),
  attendance: (groupId: string, date: string) => api.get<AttendanceRow[]>(`/teacher/attendance?group_id=${groupId}&date=${date}`),
  saveAttendance: (body: object) => api.post<AttendanceRow>("/teacher/attendance", body),
  markArrival: (childId: string) => api.post<AttendanceRow>("/teacher/attendance/arrival", { child_id: childId }),
  markDeparture: (childId: string) => api.post<AttendanceRow>("/teacher/attendance/departure", { child_id: childId }),
  patchAttendance: (id: string, body: object) => api.patch<AttendanceRow>(`/teacher/attendance/${id}`, body),
  schedule: (groupId: string) => api.get<ScheduleItem[]>(`/teacher/schedule?group_id=${groupId}`),
  groupThread: (groupId: string, audience: "all" | "teachers" = "all") => api.get<Thread>(`/teacher/groups/${groupId}/communication-thread?audience=${audience}`),
  threads: () => api.get<Thread[]>("/teacher/communications/threads"),
  messages: (threadId: string) => api.get<Message[]>(`/teacher/communications/threads/${threadId}/messages`),
  sendMessage: (threadId: string, body: string) => api.post<Message>(`/teacher/communications/threads/${threadId}/messages`, { body }),
  direct: (childId: string, guardianId: string) => api.post<Thread>("/teacher/communications/direct", { child_id: childId, guardian_id: guardianId }),
  diary: (childId: string) => api.get<DiaryEntry[]>(`/teacher/diary?child_id=${childId}`),
  createDiary: (body: object) => api.post<DiaryEntry>("/teacher/diary", body),
  updateDiary: (id: string, body: object) => api.patch<DiaryEntry>(`/teacher/diary/${id}`, body),
  announcements: (groupId: string) => api.get<Announcement[]>(`/teacher/announcements?group_id=${groupId}`),
  createAnnouncement: (body: object) => api.post<Announcement>("/teacher/announcements", body),
  updateAnnouncement: (id: string, body: object) => api.patch<Announcement>(`/teacher/announcements/${id}`, body),
  archiveAnnouncement: (id: string) => api.post<Announcement>(`/teacher/announcements/${id}/archive`),
  polls: (groupId: string) => api.get<Poll[]>(`/teacher/polls?group_id=${groupId}`),
  createPoll: (body: object) => api.post<Poll>("/teacher/polls", body),
  closePoll: (id: string) => api.post<Poll>(`/teacher/polls/${id}/close`),
  incidents: (groupId: string) => api.get<Incident[]>(`/teacher/incidents?group_id=${groupId}`),
  createIncident: (body: object) => api.post<Incident>("/teacher/incidents", body),
  resolveIncident: (id: string) => api.patch<Incident>(`/teacher/incidents/${id}`, { status: "resolved" }),
  tasks: () => api.get<TeacherTask[]>("/teacher/tasks"),
  updateTask: (id: string, status: "open" | "in_progress" | "done") => api.patch<TeacherTask>(`/teacher/tasks/${id}`, { status }),
  notifications: () => api.get<Notification[]>("/teacher/notifications"),
  readNotification: (id: string) => api.post<Notification>(`/teacher/notifications/${id}/read`),
  notices: () => api.get<DocumentNotice[]>("/teacher/document-notices"),
  acknowledgeNotice: (id: string) => api.post<DocumentNotice>(`/teacher/document-notices/${id}/ack`),
  consents: (groupId: string) => api.get<PhotoConsent[]>(`/teacher/photo-consents?group_id=${groupId}`),
  photos: (groupId: string) => api.get<PhotoAsset[]>(`/teacher/photos?group_id=${groupId}`),
  uploadPhoto: async (groupId: string, childIds: string[], file: File) => {
    const body = new FormData();
    body.append("group_id", groupId);
    childIds.forEach((id) => body.append("child_ids", id));
    body.append("file", file);
    let response: Response;
    try {
      response = await fetch(`${baseUrl}/teacher/photos`, { method: "POST", body, credentials: "include" });
    } catch { throw new NetworkError(); }
    if (!response.ok) throw new ApiError("UPLOAD_FAILED", response.status, "Не удалось загрузить фото.");
    return await response.json() as PhotoAsset;
  },
  photoContent: (id: string) => `${baseUrl}/teacher/photos/${id}/content`,
};

export const parentStage6Api = {
  children: () => api.get<ChildSummary[]>("/parent/children"),
  today: (childId: string) => api.get<ParentToday>(`/parent/children/${childId}/today`),
  announcements: () => api.get<Announcement[]>("/parent/announcements"),
  threads: () => api.get<Thread[]>("/parent/communications/threads"),
  direct: (childId: string) => api.post<Thread>("/parent/communications/direct", { child_id: childId }),
  messages: (threadId: string) => api.get<Message[]>(`/parent/communications/threads/${threadId}/messages`),
  sendMessage: (threadId: string, body: string) => api.post<Message>(`/parent/communications/threads/${threadId}/messages`, { body }),
  diary: (childId: string) => api.get<DiaryEntry[]>(`/parent/children/${childId}/diary`),
  polls: () => api.get<Poll[]>("/parent/polls"),
  vote: (pollId: string, optionId: string) => api.post<Poll>(`/parent/polls/${pollId}/vote`, { option_id: optionId }),
  photos: (childId: string) => api.get<PhotoAsset[]>(`/parent/photos?child_id=${childId}`),
  photoContent: (id: string) => `${baseUrl}/parent/photos/${id}/content`,
};
