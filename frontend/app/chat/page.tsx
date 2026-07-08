import { ChatPanel } from "@/components/chat-panel";
import { fetchLectures } from "@/lib/api";

export default async function ChatPage() {
  const lectures = await fetchLectures().catch(() => []);

  return (
    <main className="grid gap-6">
      <ChatPanel lectures={lectures} />
    </main>
  );
}
