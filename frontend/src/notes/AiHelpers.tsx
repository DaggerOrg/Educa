import { useEffect, useState } from "react";
import { ApiError } from "../api.ts";
import { IconPlus, IconSparkle } from "../components/icons.tsx";
import {
  listAssistAgents,
  runAssist,
  type AssistAgentInfo,
  type AssistResult,
  type Explanation,
  type FlashcardSet,
  type PracticeQuiz,
  type Summary,
} from "../studentAiApi.ts";

interface AiHelpersProps {
  courseId: string;
  lessonId: string;
  /** Plain text of the student's notes so far, so helpers can build on them. */
  getNotesText: () => string;
  onAddToNotes: (result: AssistResult) => void;
}

export default function AiHelpers({ courseId, lessonId, getNotesText, onAddToNotes }: AiHelpersProps) {
  const [agents, setAgents] = useState<AssistAgentInfo[]>([]);
  const [active, setActive] = useState<AssistAgentInfo | null>(null);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AssistResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAssistAgents().then(setAgents).catch(() => setError("The helpers couldn't be loaded."));
  }, []);

  function pick(agent: AssistAgentInfo) {
    setActive(agent);
    setResult(null);
    setError(null);
  }

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!active || running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await runAssist(courseId, lessonId, active.key, input.trim(), getNotesText()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That didn't work. Try again.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="notes-helpers">
      <div className="notes-helper-list" role="group" aria-label="AI helpers">
        {agents.map((a) => (
          <button
            key={a.key}
            type="button"
            className={`notes-helper-card${active?.key === a.key ? " is-active" : ""}`}
            aria-pressed={active?.key === a.key}
            onClick={() => pick(a)}
          >
            <strong><IconSparkle /> {a.label}</strong>
            <span>{a.description}</span>
          </button>
        ))}
      </div>

      {active && (
        <form className="notes-helper-form" onSubmit={run}>
          <label className="field-label" htmlFor="notes-helper-input">
            {active.needsInput ? "What should I explain?" : "Focus on something? (optional)"}
          </label>
          <textarea
            id="notes-helper-input"
            className="auth-input"
            rows={2}
            maxLength={2000}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={active.needsInput ? "e.g. Why do we add -s for he/she/it?" : "Leave empty to use this lesson and your notes"}
          />
          <button type="submit" className="btn btn-primary" disabled={running || (active.needsInput && !input.trim())}>
            {running ? "Working…" : active.label}
          </button>
        </form>
      )}

      {error && <div className="error-banner">{error}</div>}
      {result && (
        <div className="notes-helper-result">
          <ResultView result={result} />
          <button type="button" className="btn" onClick={() => onAddToNotes(result)}>
            <IconPlus /> Add to my notes
          </button>
        </div>
      )}
    </div>
  );
}

function ResultView({ result }: { result: AssistResult }) {
  if ("check_question" in result) return <ExplanationView r={result} />;
  if ("questions" in result) return <QuizView r={result} />;
  if ("cards" in result) return <FlashcardsView r={result} />;
  return <SummaryView r={result} />;
}

function ExplanationView({ r }: { r: Explanation }) {
  return (
    <div className="notes-result-block">
      <p>{r.explanation}</p>
      {r.analogy && <p><strong>Think of it like this:</strong> {r.analogy}</p>}
      <p><strong>Check yourself:</strong> {r.check_question}</p>
    </div>
  );
}

function SummaryView({ r }: { r: Summary }) {
  return (
    <div className="notes-result-block">
      <p>{r.summary}</p>
      <ul>{r.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
    </div>
  );
}

function QuizView({ r }: { r: PracticeQuiz }) {
  const [picked, setPicked] = useState<Record<number, number>>({});
  return (
    <div className="notes-result-block">
      {r.questions.map((q, qi) => {
        const choice = picked[qi];
        return (
          <fieldset className="notes-quiz-q" key={qi}>
            <legend>{qi + 1}. {q.question}</legend>
            {q.options.map((o, oi) => {
              const state = choice === undefined ? "" : oi === q.answer_index ? " is-correct" : oi === choice ? " is-wrong" : "";
              return (
                <button
                  key={oi}
                  type="button"
                  className={`notes-quiz-option${state}`}
                  disabled={choice !== undefined}
                  onClick={() => setPicked((p) => ({ ...p, [qi]: oi }))}
                >
                  {o}
                </button>
              );
            })}
            {choice !== undefined && <p className="hint">{q.explanation}</p>}
          </fieldset>
        );
      })}
      <p className="hint">Practice questions only — they're separate from your graded quiz.</p>
    </div>
  );
}

function FlashcardsView({ r }: { r: FlashcardSet }) {
  const [flipped, setFlipped] = useState<Set<number>>(new Set());
  const toggle = (i: number) =>
    setFlipped((s) => {
      const next = new Set(s);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  return (
    <div className="notes-cards">
      {r.cards.map((c, i) => (
        <button key={i} type="button" className="notes-card" onClick={() => toggle(i)} aria-label={flipped.has(i) ? "Show question" : "Show answer"}>
          <span className="field-label">{flipped.has(i) ? "Answer" : "Question"}</span>
          {flipped.has(i) ? c.back : c.front}
        </button>
      ))}
    </div>
  );
}
