/** Guardian detail route. Backend hides foreign tenant UUIDs. */
import { GuardianDetailPage } from "@/features/guardians/guardian-pages";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <GuardianDetailPage id={id} />;
}
