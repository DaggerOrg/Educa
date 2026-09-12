import { useEffect, useState } from "react";
import { fetchMyQuizAttempts, submitQuizAttempt } from "../api.ts";
import type { QuizAttemptSummary, StudentQuiz, StudentQuizAttemptResult } from "../types.ts";

interface QuizTakerProps {
  lessonId: string;
  quiz: StudentQuiz;
}

export default function QuizTaker({ lessonId, quiz }: QuizTakerProps) {
  const [selected, setSelected] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<StudentQuizAttemptResult | null>(null);
  const [attempts, setAttempts] = useState<QuizAttemptSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMyQuizAttempts(lessonId).then(setAttempts).catch(() => {});
    // Starting a fresh lesson visit shouldn't show a stale result from a
    // previously viewed quiz item.
    setResult(null);
    setSelected(null);
  }, [lessonId, quiz.quizItemId]);

  async function handleSubmit() {
    if (selected === null) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitQuizAttempt(lessonId, quiz.quizItemId, selected);
      setResult(res);
      setAttempts(await fetchMyQuizAttempts(lessonId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  function tryAgain() {
    setResult(null);
    setSelected(null);
  }

  return (
    <div className="quiz-block quiz-taker">
      <label className="field-label">Quiz</label>
      <p className="quiz-question">{quiz.question}</p>
      <div className="quiz-options-list">
        {quiz.options.map((opt, i) => {
          const isSelected = selected === i;
          const isRevealCorrect = result != null && i === result.correctIndex;
          const isRevealWrong = result != null && isSelected && !result.correct;
          return (
            <label
              key={i}
              className={`quiz-option-row${isSelected ? " is-selected" : ""}${isRevealCorrect ? " is-correct" : ""}${isRevealWrong ? " is-wrong" : ""}`}
            >
              <input
                type="radio"
                name={`quiz-${quiz.quizItemId}`}
                checked={isSelected}
                disabled={result != null}
                onChange={() => setSelected(i)}
              />
              {opt}
            </label>
          );
        })}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!result ? (
        <button
          type="button"
          className="btn btn-primary"
          disabled={selected === null || submitting}
          onClick={handleSubmit}
        >
          {submitting ? "Submitting…" : "Submit answer"}
        </button>
      ) : (
        <div className="quiz-result">
          <p className={result.correct ? "quiz-result-correct" : "quiz-result-wrong"}>
            {result.correct ? "Correct!" : "Not quite."} Score: {result.score}/{result.maxScore}
          </p>
          <button type="button" className="btn" onClick={tryAgain}>Try again</button>
        </div>
      )}

      {attempts.length > 0 && (
        <div className="quiz-attempt-history">
          <label className="field-label">Your attempts</label>
          <ul className="quiz-attempt-list">
            {attempts.map((a) => (
              <li key={a.id}>
                {a.score}/{a.maxScore} — {new Date(a.submittedAt).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
