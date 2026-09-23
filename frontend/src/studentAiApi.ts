// Client for the student notes/helpers (backend/student_ai) and module story
// videos (backend/module_video). Kept out of api.ts, which is already large
// and shared with unrelated features; it reuses that file's base URL and
// ApiError so errors look the same everywhere.
import { API_BASE, ApiError } from "./api.ts";
import { extractErrorMessage } from "./apiError.ts";
import { getToken } from "./auth.ts";

async function call<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(extractErrorMessage(body, res.statusText), res.status);
  }
  return res.json();
}

// ---- notes ------------------------------------------------------------------------------

/** Tiptap's document JSON and Excalidraw's scene JSON -- opaque to the server. */
export type NoteDoc = Record<string, unknown>;
export interface SketchScene {
  elements: unknown[];
  appState?: { viewBackgroundColor?: string };
}

export interface StoredNotes {
  doc: NoteDoc | null;
  sketch: SketchScene | null;
  updatedAt: string | null;
}

const lessonPath = (courseId: string, lessonId: string) => `/courses/${courseId}/lessons/${lessonId}`;

export const getNotes = (courseId: string, lessonId: string) =>
  call<StoredNotes>(`${lessonPath(courseId, lessonId)}/notes`);

/** Only the fields present are written, so text and sketch save independently. */
export const saveNotes = (courseId: string, lessonId: string, body: { doc?: NoteDoc | null; sketch?: SketchScene | null }) =>
  call<StoredNotes>(`${lessonPath(courseId, lessonId)}/notes`, { method: "PUT", body: JSON.stringify(body) });

// ---- helper agents ---------------------------------------------------------------------------

export interface NoteSuggestion {
  title: string;
  summary: string;
  key_points: string[];
  example: string | null;
  source: "lesson" | "general";
}

export const suggestNote = (
  courseId: string,
  lessonId: string,
  heading: string,
  surrounding: string,
  signal?: AbortSignal,
) =>
  call<NoteSuggestion>(`${lessonPath(courseId, lessonId)}/notes/suggest`, {
    method: "POST",
    body: JSON.stringify({ heading, surrounding }),
    signal,
  });

export interface AssistAgentInfo {
  key: string;
  label: string;
  description: string;
  needsInput: boolean;
}

export interface Explanation { explanation: string; analogy: string | null; check_question: string }
export interface PracticeQuestion { question: string; options: string[]; answer_index: number; explanation: string }
export interface PracticeQuiz { questions: PracticeQuestion[] }
export interface Flashcard { front: string; back: string }
export interface FlashcardSet { cards: Flashcard[] }
export interface Summary { summary: string; key_points: string[] }
export type AssistResult = Explanation | PracticeQuiz | FlashcardSet | Summary;

export const listAssistAgents = () => call<AssistAgentInfo[]>("/student-ai/agents");

export const runAssist = (courseId: string, lessonId: string, agent: string, input: string, notes: string) =>
  call<AssistResult>(`${lessonPath(courseId, lessonId)}/assist/${agent}`, {
    method: "POST",
    body: JSON.stringify({ input, notes }),
  });

// ---- module story videos ----------------------------------------------------------------------

export interface StoryScene { narration: string; on_screen_text: string; visual: string; seconds: number }
export interface StoryScript { title: string; hook: string; scenes: StoryScene[]; takeaway: string }

export type StoryStatus = "draft" | "approved" | "queued" | "rendering" | "ready" | "failed";

/** The teacher's view of a module's story (null when none exists yet). */
export interface TeacherStory {
  id: string;
  moduleId: string;
  status: StoryStatus;
  style: string;
  script: StoryScript | null;
  provider: string | null;
  kind: "storyboard" | "video" | null;
  error: string | null;
  updatedAt: string;
}

const storyPath = (moduleId: string) => `/modules/${moduleId}/story-video`;

export const getTeacherStory = (moduleId: string) => call<TeacherStory | null>(storyPath(moduleId));

export const generateStoryScript = (moduleId: string, style: string) =>
  call<TeacherStory>(`${storyPath(moduleId)}/script`, { method: "POST", body: JSON.stringify({ style }) });

export const saveStoryScript = (moduleId: string, script: StoryScript) =>
  call<TeacherStory>(`${storyPath(moduleId)}/script`, { method: "PUT", body: JSON.stringify({ script }) });

export const approveStory = (moduleId: string) =>
  call<TeacherStory>(`${storyPath(moduleId)}/approve`, { method: "POST" });

export const renderStory = (moduleId: string) =>
  call<TeacherStory>(`${storyPath(moduleId)}/render`, { method: "POST" });

export const deleteStory = (moduleId: string) => call<{ ok: boolean }>(storyPath(moduleId), { method: "DELETE" });

export interface ReadyStory { moduleId: string; week: number; title: string; kind: "storyboard" | "video" }

export interface StudentStory {
  moduleId: string;
  week: number | null;
  title: string;
  kind: "storyboard" | "video";
  script: StoryScript;
  narrator: { name: string | null };
}

export const listReadyStories = (courseId: string) => call<ReadyStory[]>(`/courses/${courseId}/story-videos`);

export const getStudentStory = (courseId: string, moduleId: string) =>
  call<StudentStory>(`/courses/${courseId}/modules/${moduleId}/story-video`);

/** A <video> tag can't send the auth header, so fetch the file and hand back an object URL. */
export async function fetchStoryVideoUrl(courseId: string, moduleId: string): Promise<string> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/courses/${courseId}/modules/${moduleId}/story-video/file`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError("Couldn't load the video", res.status);
  return URL.createObjectURL(await res.blob());
}
