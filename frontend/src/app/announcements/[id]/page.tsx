/** Announcement ID is opaque; Backend hides foreign tenant UUIDs. */
import { AnnouncementDetailPage } from "@/features/announcements/pages";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AnnouncementDetailPage id={id} />;
}
