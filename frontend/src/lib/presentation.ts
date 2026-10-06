export const relationLabels = {
  mother: "Мама",
  father: "Папа",
  legal_guardian: "Опекун",
  other: "Другое",
} as const;

export const announcementStatusLabels = {
  active: "Активно",
  archived: "Архивировано",
} as const;

export const communicationAudienceLabels = {
  all: "Вся группа",
  parents: "Родители",
  teachers: "Воспитатели",
} as const;

export const notificationKindLabels: Record<string, string> = {
  "teacher_task.assigned": "Назначена новая задача",
  "task.assigned": "Назначена задача",
  "communication.message": "Новое сообщение",
};
