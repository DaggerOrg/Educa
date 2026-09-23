// Tiny module-level pub/sub, not a React context -- toasts are pushed from
// places that aren't necessarily inside the same component subtree as
// <ToastStack/> (e.g. ApprovalCards.tsx lives inside the chat drawer, but
// toasts render at the app root so they survive the drawer closing).
export interface Toast {
  id: string;
  message: string;
  tone: "success" | "info" | "error";
}

type Listener = (toasts: Toast[]) => void;

let toasts: Toast[] = [];
const listeners = new Set<Listener>();

function emit() {
  for (const listener of listeners) listener(toasts);
}

export function subscribeToasts(listener: Listener): () => void {
  listeners.add(listener);
  listener(toasts);
  return () => listeners.delete(listener);
}

export function pushToast(message: string, tone: Toast["tone"] = "info", durationMs = 4500) {
  const id = crypto.randomUUID();
  toasts = [...toasts, { id, message, tone }];
  emit();
  setTimeout(() => dismissToast(id), durationMs);
}

export function dismissToast(id: string) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}
