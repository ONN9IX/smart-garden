import { PublicPrivacy } from "@/features/privacy/public-page";

export const metadata = { title: "Конфиденциальность — ПРОМАКС", referrer: "no-referrer" };
export default async function PrivacyPage({ searchParams }: { searchParams: Promise<{ garden?: string }> }) {
  const { garden } = await searchParams;
  const safeGarden = garden && /^[a-f0-9-]{36}$/i.test(garden) ? garden : undefined;
  return <PublicPrivacy garden={safeGarden} />;
}
