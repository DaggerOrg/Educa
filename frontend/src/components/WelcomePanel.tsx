import { IconSparkle } from "./icons.tsx";

interface WelcomePanelProps {
  onOpenChat: () => void;
}

export default function WelcomePanel({ onOpenChat }: WelcomePanelProps) {
  return (
    <div className="welcome-panel">
      <h2>Welcome — let's build your first course</h2>
      <ol className="welcome-steps">
        <li>
          <strong>Describe it.</strong> Open Ask AI and tell it what you want to teach.
        </li>
        <li>
          <strong>Review the draft.</strong> The syllabus appears here as a week-by-week outline.
        </li>
        <li>
          <strong>Approve &amp; publish.</strong> Nothing reaches students until you sign off on each lesson.
        </li>
      </ol>
      <button type="button" className="btn btn-primary welcome-cta" onClick={onOpenChat}>
        <IconSparkle /> Open Ask AI to get started
      </button>
    </div>
  );
}
