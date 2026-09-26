import { EmployeeDetailPage } from "@/features/employees/pages";
export default async function Page({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <EmployeeDetailPage id={id} />; }
