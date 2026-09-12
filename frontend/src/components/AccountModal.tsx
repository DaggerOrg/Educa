import { useState } from "react";
import { IconCheck, IconClose } from "./icons.tsx";

export type AccountModalKind = "language" | "legal" | "feedback" | "help";

interface AccountModalProps {
  kind: AccountModalKind;
  onClose: () => void;
}

const TITLES: Record<AccountModalKind, string> = {
  language: "Language",
  legal: "Legal & privacy",
  feedback: "Give feedback",
  help: "Help & docs",
};

export default function AccountModal({ kind, onClose }: AccountModalProps) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>{TITLES[kind]}</span>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>
        {kind === "language" && <LanguageBody />}
        {kind === "legal" && <LegalBody />}
        {kind === "feedback" && <FeedbackBody onClose={onClose} />}
        {kind === "help" && <HelpBody />}
      </div>
    </div>
  );
}

const LANGUAGES = ["English (United States)", "Español", "Français", "Deutsch", "Português", "日本語"];

// Mock screen -- Studio isn't localized yet, so picking anything but English
// only updates this local selection, it doesn't change the app's language.
function LanguageBody() {
  const [selected, setSelected] = useState(LANGUAGES[0]);
  return (
    <>
      <div className="account-modal-list">
        {LANGUAGES.map((lang) => (
          <button
            type="button"
            key={lang}
            className={`account-modal-row${lang === selected ? " is-selected" : ""}`}
            onClick={() => setSelected(lang)}
          >
            {lang}
            {lang === selected && <IconCheck />}
          </button>
        ))}
      </div>
      <p className="account-modal-note">Only English is fully supported today — more languages are coming.</p>
    </>
  );
}

const LEGAL_LINKS = ["Terms of Service", "Privacy Policy", "Data Retention", "Your Privacy Choices"];

// Mock screen -- Educa is pre-launch and hasn't published these yet (see
// website/'s honest "free during early access" placeholder pattern).
function LegalBody() {
  return (
    <>
      <div className="account-modal-list">
        {LEGAL_LINKS.map((label) => (
          <div className="account-modal-row is-static" key={label}>
            {label}
          </div>
        ))}
      </div>
      <p className="account-modal-note">Educa is in early access — these documents aren't published yet.</p>
    </>
  );
}

function FeedbackBody({ onClose }: { onClose: () => void }) {
  const [text, setText] = useState("");
  const [sent, setSent] = useState(false);

  if (sent) {
    return (
      <div className="account-modal-sent">
        <p>Thanks for the feedback!</p>
        <button type="button" className="btn" onClick={onClose}>Close</button>
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        setSent(true);
      }}
    >
      <label className="field-label" htmlFor="feedback-text">What's on your mind?</label>
      <textarea
        id="feedback-text"
        className="auth-input modal-textarea"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Tell us what's working, or what isn't..."
        required
      />
      <button type="submit" className="btn btn-primary auth-submit">Send feedback</button>
    </form>
  );
}

const HELP_TOPICS = ["Getting started with Studio", "Working with the AI assistant", "Publishing a course", "Selling on the Marketplace"];

// Mock screen -- no docs site exists yet, so these are static topic rows
// rather than working links.
function HelpBody() {
  return (
    <>
      <div className="account-modal-list">
        {HELP_TOPICS.map((label) => (
          <div className="account-modal-row is-static" key={label}>
            {label}
          </div>
        ))}
      </div>
      <p className="account-modal-note">Full documentation is coming soon.</p>
    </>
  );
}
