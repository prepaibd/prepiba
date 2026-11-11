export type Lang = "en" | "bn";

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string;
  role: "student" | "reviewer" | "admin";
  plan: "free" | "paid";
  ui_language: Lang;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Subject { id: string; slug: string; name: string; name_bn: string }
export interface Topic { id: string; slug: string; name: string; name_bn: string; subject: string; question_count?: number }

export interface Section {
  section_no: number;
  part_label: string;
  label: string;
  subject: string;
  question_count: number;
  scorable_count: number;
}

export interface Exam {
  slug: string;
  program: string;
  institute: string;
  session: string;
  year: number;
  month: number;
  completeness: "full" | "partial";
  question_count: number;
  scorable_count: number;
  duration_minutes: number | null;
  total_marks: string | null;
  sections?: Section[];
}

export interface Option { label: string; label_display: string; text: string; text_bn: string }
export interface Group {
  id: string;
  group_type: string;
  instruction: string;
  instruction_bn: string;
  passage: string;
  passage_bn: string;
  table: { rows: string[][] } | null;
}
export interface Figure { url: string; caption: string; role: string }

export interface Question {
  id: string;
  exam: string;
  section_no: number;
  number: number;
  subject: string;
  type: string;
  stem: string;
  stem_bn: string;
  bn_status: string;
  topic: Topic | null;
  marks: string | null;
  answer_kind: string;
  answer_status: string;
  scorable: boolean;
  options: Option[];
  group: Group | null;
  figures: Figure[];
}

export interface Response { selected: string | null; flagged: boolean; time_spent: number }

export interface AttemptSummary {
  id: string;
  mode: string;
  status: "in_progress" | "submitted" | "expired";
  server_now: string;
  exam: Exam | null;
  started_at: string;
  deadline_at: string | null;
  submitted_at: string | null;
  time_limit_seconds: number | null;
  negative_mark: number;
  score: number | null;
  max_score: number | null;
  correct: number | null;
  wrong: number | null;
  unanswered: number | null;
}

export interface AttemptDetail extends AttemptSummary {
  questions: (Question & { response: Response })[];
}

export interface Formula { slug: string; title: string; title_bn: string; body: string; body_bn: string }
export type Rule = Formula;

export interface Solution {
  body_en: string; body_bn: string;
  trap_en: string; trap_bn: string;
  trick_en: string; trick_bn: string;
  note: string;
  formulas: Formula[];
  rules: Rule[];
}

export interface Reveal {
  correct_label: string | null;
  answer_text: string;
  answer_status: string;
  answer_prev: string;
  source_defect: string;
  review_note: string;
  solution: Solution | null;
}

export type ReviewItem = Question & Reveal & {
  response: Response;
  is_correct: boolean | null;
  marks_awarded: number | null;
};

export interface Breakdown {
  id: string | number;
  label: string;
  subject: string | null;
  correct: number; wrong: number; unanswered: number; total: number;
  score: number; accuracy: number;
}

export interface AttemptResult extends AttemptSummary {
  review: ReviewItem[];
  by_section: Breakdown[];
  by_topic: Breakdown[];
}

export interface Bookmark { id: string; created_at: string; question: Question }

export interface ChatSessionSummary {
  id: string;
  title: string;
  question: { id: string; exam: string; number: number; stem: string } | null;
  created_at: string;
  updated_at: string;
}
export interface ChatMessage { id: string; role: "user" | "assistant"; content: string; created_at: string }
export interface ChatSessionDetail extends ChatSessionSummary { messages: ChatMessage[] }

export interface UsageItem { used: number; limit: number; remaining: number; resets_at: string }
export interface Usage { chat: UsageItem; writing: UsageItem }

export interface WritingPrompt {
  id: string; exam: string; session: string; year: number; number: number;
  type: "essay" | "argument"; stem: string; instruction: string; marks: string | null;
}
export interface WritingFeedback {
  overall: number; content: number; structure: number; language: number;
  summary: string; strengths: string[]; improvements: string[];
  corrections: { original: string; suggestion: string; reason: string }[];
}
export interface WritingSubmission {
  id: string; prompt: WritingPrompt; body: string; word_count: number;
  status: "done" | "failed"; feedback: WritingFeedback | null; error: string; created_at: string;
}

export interface ReviewOption { label: string; text: string; text_bn: string; is_correct: boolean }
export interface ReviewQuestion {
  id: string; exam: string; session: string; section_no: number; number: number; subject: string;
  topic: string | null; type: string; stem: string; stem_bn: string; bn_status: string;
  options: ReviewOption[]; passage: string; answer_status: string; answer_source: string;
  source_defect: string; review_note: string; solution_en: string; solution_bn: string;
}
export interface ReviewSummary {
  bangla: { draft: number; reviewed: number; missing: number };
  answers: Record<string, number>;
  flagged: number;
}

export interface TopicStat { topic_id: string; topic: string; subject: string; answered: number; correct: number; accuracy: number; avg_seconds: number }
export interface Overview {
  totals: { attempts: number; answered: number; correct: number; accuracy: number; avg_seconds_per_question: number; active_days: number; streak_days: number };
  by_subject: { subject: string; answered: number; correct: number; accuracy: number }[];
  by_topic: TopicStat[];
  weakest: TopicStat[];
  trend: { attempt_id: string; date: string; mode: string; score_pct: number }[];
  min_answers_for_weak: number;
}
export interface TopicFrequency {
  years: number[];
  topics: { id: string; name: string; subject: string; total: number; by_year: Record<string, number> }[];
}
