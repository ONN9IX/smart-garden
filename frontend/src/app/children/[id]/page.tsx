/** Child detail route. Backend hides foreign tenant UUIDs. */
import { ChildDetailPage } from "@/features/children/child-pages";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ChildDetailPage id={id} />;
}
