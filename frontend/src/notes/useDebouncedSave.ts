import { useCallback, useEffect, useRef, useState } from "react";

export type SaveState = "idle" | "saving" | "saved" | "error";

/**
 * Debounced autosave. `schedule(value)` remembers only the latest value and
 * saves it after `delayMs` of quiet; a failed save keeps the value so the next
 * change (or the unmount flush) retries it. Pending changes are flushed on
 * unmount so closing the panel never loses the last edit.
 */
export function useDebouncedSave<T>(save: (value: T) => Promise<unknown>, delayMs = 1500) {
  const [state, setState] = useState<SaveState>("idle");
  const pending = useRef<{ value: T } | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const saveRef = useRef(save);
  saveRef.current = save;

  const flush = useCallback(async () => {
    window.clearTimeout(timer.current);
    if (inFlight.current || !pending.current) return;
    const job = pending.current;
    pending.current = null;
    inFlight.current = true;
    if (mounted.current) setState("saving");
    try {
      await saveRef.current(job.value);
      inFlight.current = false;
      if (pending.current) return void flush(); // something newer arrived while saving
      if (mounted.current) setState("saved");
    } catch {
      inFlight.current = false;
      pending.current ??= job; // keep it for the next attempt, unless something newer exists
      if (mounted.current) setState("error");
    }
  }, []);

  const schedule = useCallback(
    (value: T) => {
      pending.current = { value };
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => void flush(), delayMs);
    },
    [delayMs, flush],
  );

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      void flush();
    };
  }, [flush]);

  return { state, schedule, flush };
}

/** Collapse several save states into the one the student should see. */
export function combineSaveStates(...states: SaveState[]): SaveState {
  if (states.includes("error")) return "error";
  if (states.includes("saving")) return "saving";
  if (states.includes("saved")) return "saved";
  return "idle";
}
