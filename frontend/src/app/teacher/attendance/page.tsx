import { AttendancePage } from "@/features/teacher/attendance-page";
export default async function Page({ searchParams }: { searchParams: Promise<{ group?: string }> }) {
  const { group } = await searchParams;
  return <AttendancePage initialGroupId={group} />;
}
