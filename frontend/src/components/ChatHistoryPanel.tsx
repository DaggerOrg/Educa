import { useEffect, useState } from "react";
import { fetchChatSessionTranscript, listChatSessions } from "../api.ts";
import type { ChatSession, ChatTurn } from "../types.ts";
import { IconArrowLeft } from "./icons.tsx";

interface ChatHistoryPanelProps {
  onResume: (sessionId: string) => void;
}

function timeAgo(unixSeconds: number): string {
  const diff = Date.now() / 1000 - unixSeconds;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function ChatHistoryPanel({ onResume }: ChatHistoryPanelProps) {
  const [sessions, setSessions] = useState<ChatSession[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ChatSession | null>(null);

  useEffect(() => {
    listChatSessions()
      .then(setSessions)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (selected) {
    return <ChatHistoryTranscript session={selected} onBack={() => setSelected(null)} onResume={onResume} />;
  }

  return (
    <div className="chat-history">
      {error && <div className="error-banner">{error}</div>}
      {!sessions ? (
        <p className="hint chat-history-empty">Loading…</p>
      ) : sessions.length === 0 ? (
        <p className="hint chat-history-empty">No past conversations yet — anything you ask AI here will show up next time.</p>
      ) : (
        <ul className="chat-history-list">
          {sessions.map((s) => (
            <li key={s.id}>
              <button type="button" className="chat-history-item" onClick={() => setSelected(s)}>
                <span className="chat-history-item-title">{s.title}</span>
                <span className="chat-history-item-time">{timeAgo(s.updatedAt)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface ChatHistoryTranscriptProps {
  session: ChatSession;
  onBack: () => void;
  onResume: (sessionId: string) => void;
}

function ChatHistoryTranscript({ session, onBack, onResume }: ChatHistoryTranscriptProps) {
  const [transcript, setTranscript] = useState<ChatTurn[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchChatSessionTranscript(session.id)
      .then(setTranscript)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [session.id]);

  return (
    <div className="chat-history">
      <button type="button" className="btn chat-history-back" onClick={onBack}>
        <IconArrowLeft /> All conversations
      </button>
      {error && <div className="error-banner">{error}</div>}
      {!transcript ? (
        <p className="hint chat-history-empty">Loading…</p>
      ) : (
        <div className="chat-history-transcript">
          {transcript.map((t, i) => (
            <div className={`chat-history-turn chat-history-turn-${t.role}`} key={i}>
              <span className="chat-history-turn-role">{t.role === "user" ? "You" : "AI"}</span>
              <p>{t.content}</p>
            </div>
          ))}
        </div>
      )}
      <button type="button" className="btn btn-primary chat-history-resume" onClick={() => onResume(session.id)}>
        Continue this conversation
      </button>
    </div>
  );
}
