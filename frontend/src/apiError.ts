// FastAPI's own validation errors (422s from a bad request body -- e.g. an
// email address Pydantic's EmailStr rejects) return `detail` as an array of
// {loc, msg, type} objects, not a string, unlike every hand-written
// HTTPException(status, "some string") elsewhere in the backend. Every
// fetch wrapper in this app used to do `body.detail || res.statusText`
// straight into `new Error(...)`, which silently stringified an object/
// array `detail` to the literal text "[object Object]" instead of
// whatever Pydantic actually said was wrong.
export function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (item && typeof item === "object" && "msg" in item ? String((item as { msg: unknown }).msg) : null))
        .filter((m): m is string => !!m);
      if (messages.length > 0) return messages.join("; ");
    }
  }
  return fallback;
}
