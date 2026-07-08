export type LectureStatus = "queued" | "transcribing" | "processing" | "indexing" | "done" | "failed";

export type Chapter = {
  id: number;
  subject_id: number;
  name: string;
};

export type Subject = {
  id: number;
  name: string;
  chapters: Chapter[];
  lecture_count: number;
};

export type LectureListItem = {
  id: number;
  title: string;
  original_filename: string;
  status: LectureStatus;
  word_count: number | null;
  duration_seconds: number | null;
  error_message: string | null;
  subject_id: number | null;
  subject_name: string | null;
  chapter_id: number | null;
  chapter_name: string | null;
  subsection: string | null;
  source_type: "upload" | "youtube";
  source_url: string | null;
  created_at: string;
  updated_at: string;
};

export type Transcript = {
  id: number;
  text: string;
  segments_json: Array<Record<string, unknown>>;
};

export type Section = {
  id: number;
  order_index: number;
  title: string;
  start_seconds: number | null;
  end_seconds: number | null;
  text: string;
  summary: string;
};

export type QuizItem = {
  id: number;
  question: string;
  options_json: string[];
  correct_answer: string;
  explanation: string;
};

export type ProcessingEvent = {
  id: number;
  step: string;
  status: string;
  message: string | null;
  created_at: string;
};

export type LectureDetail = LectureListItem & {
  transcript: Transcript | null;
  sections: Section[];
  quiz_items: QuizItem[];
  events: ProcessingEvent[];
};

export type UploadMeta = {
  subject?: string;
  chapter?: string;
  subsection?: string;
};

export type Citation = {
  lecture_id: number;
  lecture_title: string;
  section_id: number | null;
  section_title: string | null;
  snippet: string;
  start_seconds: number | null;
  end_seconds: number | null;
};

export type ChatResponse = {
  answer: string;
  citations: Citation[];
  session_id: number | null;
};

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
};

export type ChatSessionListItem = {
  id: number;
  title: string;
  lecture_ids: number[];
  message_count: number;
  created_at: string;
  updated_at: string;
};

export type ChatSessionDetail = {
  id: number;
  title: string;
  lecture_ids: number[];
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};

