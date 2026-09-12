import { extractErrorMessage } from "./apiError.ts";
import { getToken } from "./auth.ts";
import type {
  Course,
  CoursePreview,
  Enrollment,
  Lesson,
  Listing,
  ListingDetail,
  Material,
  Purchase,
  QuizAttemptSummary,
  StudentLesson,
  StudentQuizAttemptResult,
} from "./types.ts";

// Exported for TeacherChat.tsx, which calls this base directly (Liveblocks'
// `authEndpoint` callback needs a plain `fetch`, not `request()`'s
// JSON-response assumption).
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
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
  return res.status === 204 ? (null as T) : res.json();
}

// ---- Teacher: course authoring -------------------------------------------

export const listMyCourses = () => request<Course[]>("/courses/mine");

export const fetchCourse = (courseId: string) => request<Course>(`/courses/${courseId}`);

export const patchLesson = (lessonId: string, body: { title?: string; objective?: string }) =>
  request<Lesson>(`/lessons/${lessonId}`, { method: "PATCH", body: JSON.stringify(body) });

export const setApproval = (lessonId: string, approved: boolean) =>
  request<Lesson>(`/lessons/${lessonId}/approval`, { method: "PATCH", body: JSON.stringify({ approved }) });

export const publishLesson = (lessonId: string) =>
  request<Lesson>(`/lessons/${lessonId}/publish`, { method: "POST" });

export const resetCourse = () => request<{ ok: boolean }>("/reset", { method: "POST" });

export async function uploadMaterial(file: File): Promise<Material> {
  const body = new FormData();
  body.append("file", file);
  const token = getToken();
  // No explicit Content-Type here -- the browser sets the multipart
  // boundary itself, unlike request()'s default application/json.
  const res = await fetch(`${API_BASE}/materials`, {
    method: "POST",
    body,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) {
    const body2 = await res.json().catch(() => ({}));
    throw new ApiError(extractErrorMessage(body2, res.statusText), res.status);
  }
  return res.json();
}

export const listMaterials = () => request<Material[]>("/materials");

export const deleteMaterial = (materialId: string) =>
  request<{ ok: boolean }>(`/materials/${materialId}`, { method: "DELETE" });

// ---- Catalog + student learning experience -------------------------------

export const fetchCatalog = () => request<CoursePreview[]>("/courses");

export const enrollInCourse = (courseId: string) =>
  request<Enrollment>(`/courses/${courseId}/enroll`, { method: "POST" });

export const fetchMyEnrolledCourses = () => request<CoursePreview[]>("/students/me/courses");

export const fetchStudentLesson = (courseId: string, lessonId: string) =>
  request<StudentLesson>(`/courses/${courseId}/lessons/${lessonId}`);

export const submitQuizAttempt = (lessonId: string, quizItemId: string, selectedIndex: number) =>
  request<StudentQuizAttemptResult>(`/lessons/${lessonId}/quiz/attempts`, {
    method: "POST",
    body: JSON.stringify({ quizItemId, selectedIndex }),
  });

export const fetchMyQuizAttempts = (lessonId: string) =>
  request<QuizAttemptSummary[]>(`/lessons/${lessonId}/quiz/attempts/me`);

// ---- Marketplace: teacher-to-teacher curriculum sales ---------------------
// Buying hands the buyer an independent copy of the course (see
// backend/app/marketplace.py) -- not a link back to the seller's. Payment
// is mocked for now: `buyListing` grants the copy immediately.

export const browseListings = (q?: string) =>
  request<Listing[]>(`/marketplace/listings${q ? `?q=${encodeURIComponent(q)}` : ""}`);

export const fetchListing = (listingId: string) => request<ListingDetail>(`/marketplace/listings/${listingId}`);

export const createListing = (body: { courseId: string; title: string; description: string; priceCents: number }) =>
  request<Listing>("/marketplace/listings", { method: "POST", body: JSON.stringify(body) });

export const deactivateListing = (listingId: string) =>
  request<Listing>(`/marketplace/listings/${listingId}/deactivate`, { method: "POST" });

export const buyListing = (listingId: string) =>
  request<Course>(`/marketplace/listings/${listingId}/purchase`, { method: "POST" });

export const listMyListings = () => request<Listing[]>("/marketplace/mine/listings");

export const listMyPurchases = () => request<Purchase[]>("/marketplace/mine/purchases");
