import { Chapter, ChatResponse, ChatSessionDetail, ChatSessionListItem, LectureDetail, LectureListItem, Subject, UploadMeta } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchLectures(): Promise<LectureListItem[]> {
  const response = await fetch(`${API_BASE_URL}/lectures`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to fetch lectures");
  }
  return response.json();
}

export async function fetchLecture(id: string): Promise<LectureDetail> {
  const response = await fetch(`${API_BASE_URL}/lectures/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to fetch lecture");
  }
  return response.json();
}

export async function uploadLecture(file: File, meta: UploadMeta = {}): Promise<void> {
  const formData = new FormData();
  formData.append("file", file);
  if (meta.subject) formData.append("subject", meta.subject);
  if (meta.chapter) formData.append("chapter", meta.chapter);
  if (meta.subsection) formData.append("subsection", meta.subsection);
  const response = await fetch(`${API_BASE_URL}/lectures/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error("Upload failed");
  }
}

export async function ingestYoutube(url: string, meta: UploadMeta = {}): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/lectures/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, ...meta }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "YouTube ingest failed");
  }
}

export async function fetchSubjects(): Promise<Subject[]> {
  const response = await fetch(`${API_BASE_URL}/subjects`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to fetch subjects");
  }
  return response.json();
}

export async function createSubject(name: string): Promise<Subject> {
  const response = await fetch(`${API_BASE_URL}/subjects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new Error("Failed to create subject");
  }
  return response.json();
}

export async function createChapter(subjectId: number, name: string): Promise<Chapter> {
  const response = await fetch(`${API_BASE_URL}/subjects/${subjectId}/chapters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new Error("Failed to create chapter");
  }
  return response.json();
}

export async function retryLecture(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/lectures/${id}/retry`, { method: "POST" });
  if (!response.ok) {
    throw new Error("Retry failed");
  }
}

export async function deleteLecture(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/lectures/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Delete failed");
  }
}

export async function askQuestion(question: string, lectureIds: number[], sessionId: number | null): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, lecture_ids: lectureIds, session_id: sessionId }),
  });
  if (!response.ok) {
    throw new Error("Chat failed");
  }
  return response.json();
}

export async function fetchChatSessions(): Promise<ChatSessionListItem[]> {
  const response = await fetch(`${API_BASE_URL}/chat/sessions`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to fetch chat sessions");
  }
  return response.json();
}

export async function fetchChatSession(id: number): Promise<ChatSessionDetail> {
  const response = await fetch(`${API_BASE_URL}/chat/sessions/${id}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to fetch chat session");
  }
  return response.json();
}

export async function deleteChatSession(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/sessions/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to delete chat session");
  }
}

