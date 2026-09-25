/** Group detail route. ID is an opaque UUID; backend enforces tenant access. */
import { GroupDetailPage } from "@/features/groups/group-pages";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <GroupDetailPage id={id} />;
}
