export interface Quiz {
  question: string;
  options: string[];
  correctIndex: number;
}

export interface Slide {
  heading: string;
  bullets: string[];
}

export interface LessonContent {
  slides: Slide[];
  speakerNotes: string;
  // Slides/notes come from lesson_content_agent, the quiz from a separate
  // quiz_agent tool call -- a lesson can have one without the other yet.
  quiz: Quiz | null;
}

export interface Lesson {
  id: string;
  title: string;
  objective: string;
  content: LessonContent | null;
  approved: boolean;
  published: boolean;
}

export interface Week {
  week: number;
  title: string;
  lessons: Lesson[];
}

export interface Course {
  id: string;
  teacherId: string;
  title: string;
  audience: string;
  weeks: Week[];
}

export interface Material {
  id: string;
  filename: string;
  charCount: number;
  chunkCount: number;
}

export type Role = "teacher" | "student";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: Role;
}

// The student-facing shape of a published lesson: no `correctIndex`
// anywhere -- the server never sends it until after a quiz is submitted
// (see StudentQuizAttemptResult).
export interface StudentQuiz {
  quizItemId: string;
  question: string;
  options: string[];
}

export interface StudentLesson {
  id: string;
  title: string;
  objective: string;
  slides: Slide[];
  speakerNotes: string;
  quiz: StudentQuiz | null;
}

export interface StudentQuizAttemptResult {
  id: string;
  score: number;
  maxScore: number;
  correct: boolean;
  correctIndex: number;
  submittedAt: string;
}

export interface QuizAttemptSummary {
  id: string;
  score: number;
  maxScore: number;
  submittedAt: string;
}

export interface Enrollment {
  id: string;
  courseId: string;
  status: string;
}

// The catalog / "my enrolled courses" shape: published lessons only, title
// + objective as a table of contents -- no slides/speaker notes/quiz
// content (see backend/app/store.py's `_serialize_course_preview`). Kept
// distinct from `Course`/`Week`/`Lesson`, which are the teacher's own,
// full-content shape (all lessons, draft or published, quiz answers
// included) -- conflating the two would let a lesson from one context be
// rendered as if it were the other.
export interface LessonPreview {
  id: string;
  title: string;
  objective: string;
}

export interface WeekPreview {
  week: number;
  title: string;
  lessons: LessonPreview[];
}

export interface CoursePreview {
  id: string;
  teacherId: string;
  title: string;
  audience: string;
  weeks: WeekPreview[];
}

// A listing card, as shown in the marketplace grid -- no lesson content,
// just enough to browse/search (see backend/app/marketplace.py's
// `_serialize_listing`).
export interface Listing {
  id: string;
  courseId: string;
  sellerId: string;
  sellerName: string;
  title: string;
  description: string;
  priceCents: number;
  isActive: boolean;
  createdAt: string;
  weekCount: number;
  lessonCount: number;
  audience: string;
}

// A listing's syllabus *outline* -- week/lesson titles and objectives,
// never slides/speaker notes/quiz content. That stays behind the paywall
// until `buyListing` hands over a real, independent course copy.
export interface ListingWeekPreview {
  week: number;
  title: string;
  lessons: { title: string; objective: string }[];
}

export interface ListingDetail extends Listing {
  weeks: ListingWeekPreview[];
}

export interface Purchase {
  id: string;
  listingId: string;
  listingTitle: string | null;
  courseId: string;
  priceCents: number;
  purchasedAt: string;
}
