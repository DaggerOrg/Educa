import type { Node as PMNode } from "@tiptap/pm/model";
import type { EditorState } from "@tiptap/pm/state";

export interface HeadingCandidate {
  /** Normalized heading text -- used so the same heading is never asked about twice. */
  key: string;
  text: string;
  /** Where accepted notes go: the range [insertAt, replaceTo) is replaced by them. */
  insertAt: number;
  replaceTo: number;
  /** What the student already wrote above the heading, so suggestions don't repeat it. */
  surrounding: string;
}

const MIN_CHARS = 3;
const MAX_CHARS = 100;
const MAX_WORDS = 12;
const MAX_SURROUNDING_CHARS = 1500;
// A line that ends like a finished sentence is the student's own note, not a title.
const SENTENCE_END = /[.!;:,]$/;

export const normalizeKey = (text: string) => text.toLowerCase().replace(/\s+/g, " ").trim();

function isEmptyParagraph(node: PMNode | null): boolean {
  return !!node && node.type.name === "paragraph" && node.content.size === 0;
}

/** A heading node, or a short paragraph that reads like a title ("What is present tense"). */
export function isTitleLike(node: PMNode): boolean {
  const text = node.textContent.trim();
  if (text.length < MIN_CHARS || text.length > MAX_CHARS || !/\p{L}/u.test(text)) return false;
  if (node.type.name === "heading") return true;
  if (node.type.name !== "paragraph") return false;
  return !SENTENCE_END.test(text) && text.split(/\s+/).length <= MAX_WORDS;
}

/**
 * Is the student sitting right after a title they just wrote, with nothing
 * written under it yet? Two shapes count:
 *   - the cursor is at the end of a title-like line, or
 *   - the cursor is on the empty line directly below one (they pressed Enter).
 * Only top-level blocks count -- lines inside lists or quotes are never titles.
 */
export function findHeadingCandidate(state: EditorState): HeadingCandidate | null {
  const { selection, doc } = state;
  if (!selection.empty) return null;
  const $from = selection.$from;
  if ($from.depth !== 1) return null;

  const current = $from.parent;
  const index = $from.index(0);

  let titleIndex: number;
  let insertAt: number;
  let replaceTo: number;
  let belowIndex: number;

  if (isEmptyParagraph(current)) {
    // Cursor on the empty line under the title.
    if (index === 0) return null;
    titleIndex = index - 1;
    insertAt = $from.before();
    replaceTo = $from.after();
    belowIndex = index + 1;
  } else {
    // Cursor at the end of the title line itself.
    if ($from.parentOffset !== current.content.size) return null;
    titleIndex = index;
    insertAt = $from.after();
    belowIndex = index + 1;
    const below = belowIndex < doc.childCount ? doc.child(belowIndex) : null;
    replaceTo = isEmptyParagraph(below) ? insertAt + below!.nodeSize : insertAt;
    if (isEmptyParagraph(below)) belowIndex += 1;
  }

  const title = doc.child(titleIndex);
  if (!isTitleLike(title)) return null;

  // The space under the title must be empty: the student hasn't started writing there.
  if (belowIndex < doc.childCount) return null;

  let surrounding = "";
  for (let i = 0; i < titleIndex; i += 1) surrounding += `${doc.child(i).textContent}\n`;

  const text = title.textContent.trim();
  return {
    key: normalizeKey(text),
    text,
    insertAt,
    replaceTo,
    surrounding: surrounding.trim().slice(-MAX_SURROUNDING_CHARS),
  };
}
