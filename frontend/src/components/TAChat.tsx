import { useEffect, useState } from "react";
import { ApiError, askTeachingAssistant, fetchCourseTa } from "../api.ts";
import type { ChatTurn, TeachingAssistant } from "../types.ts";
import { IconChat, IconClose } from "./icons.tsx";

interface TAChatProps {
  courseId: string;
}

// Plain fetch-based chat, not <CopilotChat> -- the TA is a per-course
// Agent built fresh per request (see backend/app/teaching_assistant.py),
// not routed through the teacher-only /agui team, so there's no AG-UI
// connection to hang a CopilotKit component off of here.
export default function TAChat({ courseId }: TAChatProps) {
  const [ta, setTa] = useState<TeachingAssistant | null>(null);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCourseTa(courseId).then(setTa).catch(() => setTa(null));
  }, [courseId]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    setError(null);
    const history = messages;
    setMessages([...history, { role: "user", content: text }]);
    setInput("");
    try {
      const { reply } = await askTeachingAssistant(courseId, text, history);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The Teaching Assistant is unavailable right now.");
    } finally {
      setSending(false);
    }
  }

  if (!ta) return null;

  return (
    <>
      <button type="button" className={`btn exercises-chat-btn${open ? " is-active" : ""}`} onClick={() => setOpen((v) => !v)}>
        <IconChat /> Ask {ta.name}
      </button>

      {open && (
        <>
          <div className="chat-backdrop" onClick={() => setOpen(false)} />
          <aside className="chat-drawer dark">
            <div className="chat-drawer-head">
              <span>{ta.name}</span>
              <button type="button" className="chat-drawer-close" onClick={() => setOpen(false)} aria-label={`Close chat with ${ta.name}`}>
                <IconClose />
              </button>
            </div>
            <div className="ta-chat-body">
              {messages.length === 0 && (
                <p className="hint ta-chat-empty">Ask {ta.name} about this course — questions, hints, or an explanation.</p>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`ta-chat-bubble ta-chat-bubble-${m.role}`}>{m.content}</div>
              ))}
              {sending && <div className="ta-chat-bubble ta-chat-bubble-assistant ta-chat-thinking">Thinking…</div>}
              {error && <div className="error-banner">{error}</div>}
            </div>
            <form className="ta-chat-input-row" onSubmit={handleSend}>
              <input
                className="auth-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a message…"
                disabled={sending}
              />
              <button type="submit" className="btn btn-primary" disabled={sending || !input.trim()}>Send</button>
            </form>
          </aside>
        </>
      )}
    </>
  );
}
