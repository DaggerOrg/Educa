import type { Editor } from "@tiptap/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api.ts";
import type { NoteSuggestion } from "../studentAiApi.ts";
import { suggestionToContent } from "./content.ts";
import { findHeadingCandidate, type HeadingCandidate } from "./headingDetection.ts";

export type AmbientState =
  | { status: "idle" }
  | { status: "loading"; candidate: HeadingCandidate }
  | { status: "ready"; candidate: HeadingCandidate; suggestion: NoteSuggestion }
  | { status: "limit" }
  | { status: "error" };

interface Options {
  editor: Editor | null;
  enabled: boolean;
  fetchSuggestion: (heading: string, surrounding: string, signal: AbortSignal) => Promise<NoteSuggestion>;
  /** How long the student must stop typing before the helper looks. */
  delayMs?: number;
}

/**
 * Watches the note editor and, once the student has written a title and
 * paused, asks the helper for notes on it and holds the answer until they
 * accept or reject it. Cost-conscious by design: it only ever asks about a
 * title-like line with nothing written under it (see headingDetection.ts),
 * only after an edit followed by a pause, never again for a heading the
 * student rejected, cancels in-flight requests when they keep typing, and
 * stops for the session once the daily limit is hit.
 */
export function useAmbientSuggestions({ editor, enabled, fetchSuggestion, delayMs = 1000 }: Options) {
  const [state, setState] = useState<AmbientState>({ status: "idle" });
  const stateRef = useRef(state);
  stateRef.current = state;

  const dismissed = useRef(new Set<string>());
  const abort = useRef<AbortController | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const limitHit = useRef(false);
  const fetchRef = useRef(fetchSuggestion);
  fetchRef.current = fetchSuggestion;

  const cancel = useCallback(() => {
    window.clearTimeout(timer.current);
    abort.current?.abort();
    abort.current = null;
  }, []);

  const reset = useCallback(() => {
    cancel();
    setState((s) => (s.status === "idle" ? s : { status: "idle" }));
  }, [cancel]);

  useEffect(() => {
    if (!editor || !enabled) {
      reset();
      return;
    }

    const look = () => {
      if (limitHit.current || editor.isDestroyed) return;
      const candidate = findHeadingCandidate(editor.state);
      if (!candidate || dismissed.current.has(candidate.key)) return;

      const controller = new AbortController();
      abort.current = controller;
      setState({ status: "loading", candidate });

      fetchRef
        .current(candidate.text, candidate.surrounding, controller.signal)
        .then((suggestion) => {
          if (controller.signal.aborted || editor.isDestroyed) return;
          // Still sitting under the same title? Otherwise the answer is stale.
          const now = findHeadingCandidate(editor.state);
          if (now?.key !== candidate.key) return setState({ status: "idle" });
          setState({ status: "ready", candidate: now, suggestion });
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          if (err instanceof ApiError && err.status === 429) {
            limitHit.current = true;
            return setState({ status: "limit" });
          }
          setState({ status: "error" });
          window.setTimeout(() => setState((s) => (s.status === "error" ? { status: "idle" } : s)), 4000);
        });
    };

    // Any edit means the student is still writing: drop what's showing and
    // start the pause timer again.
    const onUpdate = () => {
      cancel();
      if (stateRef.current.status !== "idle" && stateRef.current.status !== "limit") setState({ status: "idle" });
      timer.current = window.setTimeout(look, delayMs);
    };
    // Moving the cursor away from the title also hides a pending suggestion.
    const onSelection = () => {
      const s = stateRef.current;
      if (s.status === "ready" || s.status === "loading") {
        if (findHeadingCandidate(editor.state)?.key !== s.candidate.key) reset();
      }
    };

    editor.on("update", onUpdate);
    editor.on("selectionUpdate", onSelection);
    return () => {
      editor.off("update", onUpdate);
      editor.off("selectionUpdate", onSelection);
      cancel();
    };
  }, [editor, enabled, delayMs, cancel, reset]);

  const accept = useCallback(() => {
    const s = stateRef.current;
    if (!editor || s.status !== "ready") return;
    const { insertAt, replaceTo } = s.candidate;
    editor
      .chain()
      .focus()
      .insertContentAt({ from: insertAt, to: replaceTo }, suggestionToContent(s.suggestion))
      .run();
    setState({ status: "idle" });
  }, [editor]);

  const reject = useCallback(() => {
    const s = stateRef.current;
    if (s.status === "ready" || s.status === "loading") dismissed.current.add(s.candidate.key);
    reset();
  }, [reset]);

  return { state, accept, reject };
}
