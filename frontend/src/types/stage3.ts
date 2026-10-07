export type EmployeeCategory = "teacher" | "administrator" | "other";
export type EmployeeAccount = { id: string; username: string; role: "ADMIN" | "TEACHER"; status: "active" | "blocked"; must_change_password: boolean };
export type EmployeeFields = { first_name: string; last_name: string; middle_name: string | null; position: string; category: EmployeeCategory; phone: string | null; email: string | null };
export type EmployeeSummary = EmployeeFields & { id: string; status: "active" | "archived"; account: EmployeeAccount | null };
export type Employee = EmployeeSummary & { archived_at: string | null; created_at: string; updated_at: string };
export type TemporaryCredentials = { account: EmployeeAccount; temporary_password: string };
export type AttendanceStatus = "present" | "absent" | "unknown";
export type AttendanceRow = {
  record_id: string | null; date: string;
  child: { id: string; first_name: string; last_name: string; middle_name: string | null; status: "active" | "archived" };
  group: { id: string; name: string };
  status: AttendanceStatus; arrival_time: string | null; departure_time: string | null;
};
export type AttendanceDetail = AttendanceRow & { created_at: string; updated_at: string; created_by: string; updated_by: string };
