import type { OperatingProfile } from "@/types/auth";
import type { Role } from "@/types/auth";

export const organizationTerms = (profile: OperatingProfile) => profile === "GYMNASTICS" ? {
  child: "спортсмен", children: "спортсмены", group: "группа", groups: "группы",
  guardian: "представитель", guardians: "представители", teacherPlural: "тренеры",
  organization: "спортивную секцию",
  organizationGenitive: "спортивной секции",
  registrationSuccess: "Спортивная секция зарегистрирована",
  director: "Тренер — владелец секции", teacher: "Тренер", attendance: "Посещаемость",
  onSite: "На тренировке", absent: "Отсутствуют", schedule: "Расписание тренировок",
} : {
  child: "ребёнок", children: "дети", group: "группа", groups: "группы",
  guardian: "родитель", guardians: "родители", teacherPlural: "воспитатели",
  organization: "сад",
  organizationGenitive: "сада",
  registrationSuccess: "Сад зарегистрирован",
  director: "Директор", teacher: "Воспитатель", attendance: "Посещаемость",
  onSite: "В саду", absent: "Отсутствуют", schedule: "Расписание",
};

export function roleLabel(role: Role, profile: OperatingProfile) {
  if (profile === "GYMNASTICS") {
    if (role === "DIRECTOR") return "Тренер · владелец секции";
    if (role === "TEACHER") return "Тренер · назначенные группы";
  }
  return ({ DIRECTOR: "Директор", ADMIN: "Администратор", TEACHER: "Воспитатель", PARENT: "Родитель" } as const)[role];
}
