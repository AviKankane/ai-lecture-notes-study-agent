import { LectureTable } from "@/components/lecture-table";
import { UploadPanel } from "@/components/upload-panel";
import { fetchLectures } from "@/lib/api";

export default async function HomePage() {
  const lectures = await fetchLectures().catch(() => []);

  return (
    <main className="grid gap-6">
      <UploadPanel />
      <LectureTable lectures={lectures} />
    </main>
  );
}

