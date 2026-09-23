// Local, browser-persisted mock data backing the Traditional view's
// gradebook/roster/discussion/assignment features (see
// docs/moodle/mind-map/README.md's gap list). The backend has no
// teacher-facing "list enrollments," forum, assignment, or grade-rollup
// endpoints yet -- this fakes a plausible class around the real course/
// lesson data so those views aren't empty, using the same shapes a future
// API could return. Real quiz scores (the one part the backend already
// tracks per-student) are read live via the API in Gradebook.tsx, not
// mocked here.

const VERSION = "v1";

function readJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJSON(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage full/unavailable -- callers re-derive from the return value,
    // so a failed write just means this change doesn't persist.
  }
}

/** Deterministic pseudo-score in [min,max], stable across reloads for a given seed. */
export function seededScore(seed: string, min = 60, max = 100): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return min + (h % (max - min + 1));
}

// --- Roster -------------------------------------------------------------

export type EnrollMethod = "self" | "manual" | "cohort";

export interface RosterStudent {
  id: string;
  name: string;
  email: string;
  method: EnrollMethod;
  enrolledAt: string;
}

const SEED_NAMES = ["Ava Martinez", "Liam Chen", "Noah Patel", "Maya Johnson", "Sofia Rossi"];

function rosterKey(courseId: string) {
  return `educa.roster.${VERSION}.${courseId}`;
}

function seedRoster(courseId: string): RosterStudent[] {
  const now = Date.now();
  return SEED_NAMES.map((name, i) => ({
    id: `seed-${courseId}-${i}`,
    name,
    email: `${name.toLowerCase().replace(" ", ".")}@example.com`,
    method: "self",
    enrolledAt: new Date(now - (SEED_NAMES.length - i) * 86_400_000).toISOString(),
  }));
}

export function getRoster(courseId: string): RosterStudent[] {
  const existing = readJSON<RosterStudent[] | null>(rosterKey(courseId), null);
  if (existing) return existing;
  const seeded = seedRoster(courseId);
  writeJSON(rosterKey(courseId), seeded);
  return seeded;
}

export function enrollManually(courseId: string, name: string, email: string): RosterStudent[] {
  const roster = getRoster(courseId);
  if (roster.some((s) => s.email.toLowerCase() === email.toLowerCase())) return roster;
  const next = [
    ...roster,
    { id: `manual-${crypto.randomUUID()}`, name, email, method: "manual" as const, enrolledAt: new Date().toISOString() },
  ];
  writeJSON(rosterKey(courseId), next);
  return next;
}

export function enrollBulk(courseId: string, emails: string[]): RosterStudent[] {
  let roster = getRoster(courseId);
  for (const raw of emails) {
    const email = raw.trim();
    if (!email || roster.some((s) => s.email.toLowerCase() === email.toLowerCase())) continue;
    const localPart = email.split("@")[0] ?? email;
    const name = localPart
      .split(/[._]/)
      .filter(Boolean)
      .map((p) => p[0].toUpperCase() + p.slice(1))
      .join(" ") || email;
    roster = [...roster, { id: `cohort-${crypto.randomUUID()}`, name, email, method: "cohort", enrolledAt: new Date().toISOString() }];
  }
  writeJSON(rosterKey(courseId), roster);
  return roster;
}

export function unenroll(courseId: string, studentId: string): RosterStudent[] {
  const next = getRoster(courseId).filter((s) => s.id !== studentId);
  writeJSON(rosterKey(courseId), next);
  return next;
}

// --- Completion -----------------------------------------------------------

function completionKey(userId: string, courseId: string) {
  return `educa.completion.${VERSION}.${userId}.${courseId}`;
}

export function getCompletedLessonIds(userId: string, courseId: string): Set<string> {
  return new Set(readJSON<string[]>(completionKey(userId, courseId), []));
}

export function setLessonComplete(userId: string, courseId: string, lessonId: string, complete: boolean): Set<string> {
  const ids = getCompletedLessonIds(userId, courseId);
  if (complete) ids.add(lessonId);
  else ids.delete(lessonId);
  writeJSON(completionKey(userId, courseId), [...ids]);
  return ids;
}

// --- Assignments ------------------------------------------------------

export interface AssignmentSubmission {
  studentId: string;
  studentName: string;
  text: string;
  submittedAt: string;
  grade: number | null;
  feedback: string;
}

function assignmentKey(courseId: string, lessonId: string) {
  return `educa.assignment.${VERSION}.${courseId}.${lessonId}`;
}

function seedSubmissions(courseId: string, lessonId: string): Record<string, AssignmentSubmission> {
  const sample = getRoster(courseId).slice(0, 2);
  const out: Record<string, AssignmentSubmission> = {};
  sample.forEach((s, i) => {
    out[s.id] = {
      studentId: s.id,
      studentName: s.name,
      text: "This connected to something we covered earlier -- I'd apply it by walking through a real example step by step.",
      submittedAt: new Date(Date.now() - (i + 1) * 3_600_000).toISOString(),
      grade: i === 0 ? seededScore(`${lessonId}-${s.id}`, 70, 98) : null,
      feedback: i === 0 ? "Good connection -- be more specific about the example next time." : "",
    };
  });
  return out;
}

export function getSubmissions(courseId: string, lessonId: string): AssignmentSubmission[] {
  const existing = readJSON<Record<string, AssignmentSubmission> | null>(assignmentKey(courseId, lessonId), null);
  const map = existing ?? seedSubmissions(courseId, lessonId);
  if (!existing) writeJSON(assignmentKey(courseId, lessonId), map);
  return Object.values(map).sort((a, b) => a.submittedAt.localeCompare(b.submittedAt));
}

export function submitAssignment(
  courseId: string,
  lessonId: string,
  studentId: string,
  studentName: string,
  text: string,
): AssignmentSubmission[] {
  const map = readJSON<Record<string, AssignmentSubmission>>(assignmentKey(courseId, lessonId), {});
  map[studentId] = { studentId, studentName, text, submittedAt: new Date().toISOString(), grade: null, feedback: "" };
  writeJSON(assignmentKey(courseId, lessonId), map);
  return Object.values(map);
}

export function gradeSubmission(
  courseId: string,
  lessonId: string,
  studentId: string,
  grade: number,
  feedback: string,
): AssignmentSubmission[] {
  const map = readJSON<Record<string, AssignmentSubmission>>(assignmentKey(courseId, lessonId), {});
  if (map[studentId]) {
    map[studentId].grade = grade;
    map[studentId].feedback = feedback;
  }
  writeJSON(assignmentKey(courseId, lessonId), map);
  return Object.values(map);
}

// --- Discussion (forum) -------------------------------------------------

export interface ForumPost {
  id: string;
  authorId: string;
  authorName: string;
  authorRole: "teacher" | "student";
  body: string;
  createdAt: string;
}

function forumKey(courseId: string, lessonId: string) {
  return `educa.forum.${VERSION}.${courseId}.${lessonId}`;
}

function seedPosts(courseId: string, lessonTitle: string): ForumPost[] {
  const sample = getRoster(courseId).slice(0, 2);
  const templates = [
    `Anyone else find "${lessonTitle}" clicked once you saw the example? Took me a re-read.`,
    "Quick question on this one -- is there a real-world case where this doesn't apply?",
  ];
  const now = Date.now();
  return sample.map((s, i) => ({
    id: `seed-${courseId}-${i}`,
    authorId: s.id,
    authorName: s.name,
    authorRole: "student" as const,
    body: templates[i % templates.length],
    createdAt: new Date(now - (sample.length - i) * 5_400_000).toISOString(),
  }));
}

export function getPosts(courseId: string, lessonId: string, lessonTitle: string): ForumPost[] {
  const existing = readJSON<ForumPost[] | null>(forumKey(courseId, lessonId), null);
  if (existing) return existing;
  const seeded = seedPosts(courseId, lessonTitle);
  writeJSON(forumKey(courseId, lessonId), seeded);
  return seeded;
}

export function addPost(
  courseId: string,
  lessonId: string,
  lessonTitle: string,
  authorId: string,
  authorName: string,
  authorRole: "teacher" | "student",
  body: string,
): ForumPost[] {
  const posts = getPosts(courseId, lessonId, lessonTitle);
  const next = [...posts, { id: crypto.randomUUID(), authorId, authorName, authorRole, body, createdAt: new Date().toISOString() }];
  writeJSON(forumKey(courseId, lessonId), next);
  return next;
}

// --- Gradebook aggregation ------------------------------------------------

const QUIZ_WEIGHT = 0.6;
const ASSIGNMENT_WEIGHT = 0.4;

/** Weighted course grade (quizzes 60%, assignments 40%), skipping categories with no graded items. */
export function aggregateGrade(quizPercents: number[], assignmentPercents: number[]): number | null {
  const quizAvg = quizPercents.length ? quizPercents.reduce((a, b) => a + b, 0) / quizPercents.length : null;
  const asgAvg = assignmentPercents.length ? assignmentPercents.reduce((a, b) => a + b, 0) / assignmentPercents.length : null;
  if (quizAvg == null) return asgAvg;
  if (asgAvg == null) return quizAvg;
  return quizAvg * QUIZ_WEIGHT + asgAvg * ASSIGNMENT_WEIGHT;
}
