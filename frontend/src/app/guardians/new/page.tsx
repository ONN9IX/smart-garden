/** Guardian creation route. */
import { NewGuardianPage } from "@/features/guardians/guardian-pages";

export default async function Page({ searchParams }: { searchParams: Promise<{ child_id?: string }> }) {
  const { child_id } = await searchParams;
  return <NewGuardianPage childId={child_id} />;
}
