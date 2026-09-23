import type { JSONContent } from "@tiptap/react";
import type { AssistResult, Explanation, FlashcardSet, NoteSuggestion, PracticeQuiz, Summary } from "../studentAiApi.ts";

const text = (value: string, marks?: { type: string }[]): JSONContent => ({ type: "text", text: value, ...(marks ? { marks } : {}) });
const paragraph = (...content: JSONContent[]): JSONContent => (content.length ? { type: "paragraph", content } : { type: "paragraph" });
const heading = (level: number, value: string): JSONContent => ({ type: "heading", attrs: { level }, content: [text(value)] });
const bullets = (items: string[]): JSONContent => ({
  type: "bulletList",
  content: items.map((item) => ({ type: "listItem", content: [paragraph(text(item))] })),
});
const labelled = (label: string, value: string): JSONContent => paragraph(text(`${label}: `, [{ type: "bold" }]), text(value));

/** The editor content for an accepted note suggestion, ending in an empty line to keep typing on. */
export function suggestionToContent(s: NoteSuggestion): JSONContent[] {
  const out: JSONContent[] = [];
  if (s.summary.trim()) out.push(paragraph(text(s.summary.trim())));
  if (s.key_points.length) out.push(bullets(s.key_points));
  if (s.example?.trim()) out.push(labelled("Example", s.example.trim()));
  out.push(paragraph());
  return out;
}

function explanationToContent(r: Explanation): JSONContent[] {
  const out = [heading(3, "Explanation"), paragraph(text(r.explanation))];
  if (r.analogy) out.push(labelled("Think of it like this", r.analogy));
  out.push(labelled("Check yourself", r.check_question));
  return out;
}

function quizToContent(r: PracticeQuiz): JSONContent[] {
  const out: JSONContent[] = [heading(3, "Practice questions")];
  r.questions.forEach((q, i) => {
    out.push(paragraph(text(`${i + 1}. ${q.question}`, [{ type: "bold" }])));
    out.push(bullets(q.options.map((o, oi) => `${String.fromCharCode(97 + oi)}) ${o}`)));
    out.push(labelled("Answer", `${String.fromCharCode(97 + q.answer_index)}) ${q.options[q.answer_index]} — ${q.explanation}`));
  });
  return out;
}

function flashcardsToContent(r: FlashcardSet): JSONContent[] {
  return [heading(3, "Flashcards"), bullets(r.cards.map((c) => `${c.front} — ${c.back}`))];
}

function summaryToContent(r: Summary): JSONContent[] {
  return [heading(3, "Summary"), paragraph(text(r.summary)), bullets(r.key_points)];
}

/** Editor content for a helper's answer, for the "Add to notes" button. */
export function assistToContent(result: AssistResult): JSONContent[] {
  if ("check_question" in result) return [...explanationToContent(result), paragraph()];
  if ("questions" in result) return [...quizToContent(result), paragraph()];
  if ("cards" in result) return [...flashcardsToContent(result), paragraph()];
  return [...summaryToContent(result), paragraph()];
}
