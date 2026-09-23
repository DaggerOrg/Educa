import { CopilotChat, useCopilotKit, useAgent } from "@copilotkit/react-core/v2";
import { useState } from "react";
import { formatPrice } from "../format.ts";
import { STARTER_SUGGESTIONS } from "../starterSuggestions.ts";
import { useTheme } from "../theme.ts";
import type { Course, Listing } from "../types.ts";
import ChatHistoryPanel from "./ChatHistoryPanel.tsx";
import { IconArrowLeft, IconClock, IconPlus, IconTag } from "./icons.tsx";
import RoutinePanel from "./RoutinePanel.tsx";

interface HomeProps {
  courses: Course[];
  listings: Listing[];
  onOpenCourse: (courseId: string) => void;
  onNewCourse: () => void;
  onStartChat: () => void;
  onListCourse: (course: Course) => void;
  onUnlist: (listing: Listing) => void;
}

export default function Home({ courses, listings, onOpenCourse, onNewCourse, onStartChat, onListCourse, onUnlist }: HomeProps) {
  const [prompt, setPrompt] = useState("");
  const [sending, setSending] = useState(false);
  const [chatStarted, setChatStarted] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  // A fresh id per "conversation" on Home -- same convention as App.tsx's
  // chat drawer (`chatThreadId`), so a teacher can browse past Home
  // conversations and jump back into one, not just whatever thread happened
  // to be live when they last left this page.
  const [threadId, setThreadId] = useState<string>(() => crypto.randomUUID());
  const theme = useTheme();
  const { agent } = useAgent({ agentId: "curriculum_team" });
  const { copilotkit } = useCopilotKit();

  const listingByCourse = new Map(listings.filter((l) => l.isActive).map((l) => [l.courseId, l]));

  async function submitPrompt(text: string) {
    const message = text.trim();
    if (!message || sending) return;
    setSending(true);
    onStartChat();
    // `agent` is the one shared "curriculum_team" instance. Connect it to
    // this Home conversation's thread and queue the message *before*
    // mounting <CopilotChat threadId={threadId}> below (via setChatStarted)
    // -- mounting first races this against CopilotChat's own connect-on-
    // mount effect, which resets local messages for a thread it hasn't
    // seen yet, and would silently wipe the just-typed message if it ran
    // after addMessage but before runAgent read it.
    agent.threadId = threadId;
    await copilotkit.connectAgent({ agent });
    agent.addMessage({ id: crypto.randomUUID(), role: "user", content: message });
    // Flip to the chat view now, before the agent replies -- the "turns
    // into a ChatGPT-style conversation" moment shouldn't wait on the full
    // response, just on the (fast, local) connect above.
    setChatStarted(true);
    try {
      await copilotkit.runAgent({ agent });
    } finally {
      setSending(false);
    }
  }

  function startNewConversation() {
    setThreadId(crypto.randomUUID());
    setHistoryOpen(false);
    setChatStarted(false);
  }

  if (chatStarted || historyOpen) {
    return (
      <div className="home-hub is-chat">
        {/* `dark` only under Studio's own dark theme -- CopilotKit v2's
            stylesheet keys its dark palette off a literal `.dark` ancestor
            class, so it must track the app's real theme, not always be on
            (that was the "chat is black in light mode" bug, fixed here the
            same way as App.tsx's .chat-drawer). */}
        <div className={`home-chat${theme === "dark" ? " dark" : ""}`}>
          <div className="home-chat-head">
            <button
              type="button"
              className="home-chat-back"
              onClick={() => {
                setChatStarted(false);
                setHistoryOpen(false);
              }}
              aria-label="Back to Home"
            >
              <IconArrowLeft />
            </button>
            <span>{historyOpen ? "Past conversations" : "Ask AI"}</span>
            <div className="chat-drawer-head-actions home-chat-head-actions">
              {!historyOpen && (
                <button
                  type="button"
                  className="chat-drawer-icon-btn"
                  onClick={startNewConversation}
                  title="New conversation"
                  aria-label="Start a new conversation"
                >
                  <IconPlus />
                </button>
              )}
              <button
                type="button"
                className={`chat-drawer-icon-btn${historyOpen ? " is-active" : ""}`}
                onClick={() => setHistoryOpen((v) => !v)}
                title={historyOpen ? "Back to chat" : "Past conversations"}
                aria-label={historyOpen ? "Back to chat" : "Past conversations"}
              >
                <IconClock />
              </button>
            </div>
          </div>
          {historyOpen ? (
            <ChatHistoryPanel
              onResume={(sessionId) => {
                setThreadId(sessionId);
                setHistoryOpen(false);
                setChatStarted(true);
              }}
            />
          ) : (
            // v2's CopilotChat has no `instructions` prop -- that was a silent
            // no-op in the pre-TS JS version. The agent's real instructions
            // live server-side in backend/app/agents/curriculum/agent.py.
            <CopilotChat key={threadId} agentId="curriculum_team" threadId={threadId} />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="home-hub">
      <div className="home-prompt-section">
        <div className="home-prompt-head">
          <h2>What will you build today?</h2>
          <button
            type="button"
            className="chat-drawer-icon-btn"
            onClick={() => setHistoryOpen(true)}
            title="Past conversations"
            aria-label="Past conversations"
          >
            <IconClock />
          </button>
        </div>
        <form
          className="home-prompt-form"
          onSubmit={(e) => {
            e.preventDefault();
            submitPrompt(prompt);
            setPrompt("");
          }}
        >
          <input
            className="auth-input home-prompt-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the course you want to build…"
            disabled={sending}
          />
          <button type="submit" className="btn btn-primary" disabled={sending || !prompt.trim()}>
            {sending ? "Starting…" : "Start building"}
          </button>
        </form>
        <div className="home-suggestions">
          {STARTER_SUGGESTIONS.map((s) => (
            <button
              type="button"
              key={s.title}
              className="home-suggestion-chip"
              disabled={sending}
              onClick={() => submitPrompt(s.message)}
            >
              {s.title}
            </button>
          ))}
        </div>
      </div>

      <div className="home-materials-section">
        <h3>Bring in what you know</h3>
        <RoutinePanel />
      </div>

      <div className="courses-list-head">
        <h2>Continue building</h2>
        <button type="button" className="btn btn-primary" onClick={onNewCourse}>
          <IconPlus /> New course
        </button>
      </div>

      {courses.length === 0 ? (
        <p className="hint">No courses yet — describe one above, or buy one from the Marketplace.</p>
      ) : (
        <div className="course-card-grid">
          {courses.map((course) => {
            const weekCount = course.weeks.length;
            const lessonCount = course.weeks.reduce((n, w) => n + w.lessons.length, 0);
            const listing = listingByCourse.get(course.id);
            return (
              <div className="course-card" key={course.id}>
                <button type="button" className="course-card-main" onClick={() => onOpenCourse(course.id)}>
                  <h3>{course.title}</h3>
                  <p className="course-card-audience">{course.audience || "No audience set"}</p>
                  <span className="course-card-meta">
                    {weekCount} week{weekCount === 1 ? "" : "s"} · {lessonCount} lesson{lessonCount === 1 ? "" : "s"}
                  </span>
                </button>
                <div className="course-card-footer">
                  {listing ? (
                    <>
                      <span className="status-pill status-approved course-card-listed">
                        <IconTag /> Listed · {formatPrice(listing.priceCents)}
                      </span>
                      <button type="button" className="btn course-card-unlist" onClick={() => onUnlist(listing)}>
                        Unlist
                      </button>
                    </>
                  ) : (
                    <button type="button" className="btn" onClick={() => onListCourse(course)}>
                      List on Marketplace
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
