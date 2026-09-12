import { CopilotChat, useCopilotKit, useAgent } from "@copilotkit/react-core/v2";
import { useState } from "react";
import { formatPrice } from "../format.ts";
import { STARTER_SUGGESTIONS } from "../starterSuggestions.ts";
import type { Course, Listing } from "../types.ts";
import { IconArrowLeft, IconPlus, IconTag } from "./icons.tsx";
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
  const { agent } = useAgent({ agentId: "curriculum_team" });
  const { copilotkit } = useCopilotKit();

  const listingByCourse = new Map(listings.filter((l) => l.isActive).map((l) => [l.courseId, l]));

  async function submitPrompt(text: string) {
    const message = text.trim();
    if (!message || sending) return;
    setSending(true);
    onStartChat();
    // Flip to the chat view immediately on submit, before the agent replies --
    // this is the "turns into a ChatGPT-style conversation" moment, not
    // something that waits on the first response.
    setChatStarted(true);
    agent.addMessage({ id: crypto.randomUUID(), role: "user", content: message });
    try {
      await copilotkit.runAgent({ agent });
    } finally {
      setSending(false);
    }
  }

  if (chatStarted) {
    return (
      <div className="home-hub is-chat">
        {/* `dark` -- same convention App.tsx's .chat-drawer uses: CopilotKit
            v2's stylesheet keys its dark palette off a literal `.dark`
            ancestor class, so without it CopilotChat renders light
            regardless of Studio's own black palette. */}
        <div className="home-chat dark">
          <div className="home-chat-head">
            <button
              type="button"
              className="home-chat-back"
              onClick={() => setChatStarted(false)}
              aria-label="Back to Home"
            >
              <IconArrowLeft />
            </button>
            <span>Ask AI</span>
          </div>
          {/* v2's CopilotChat has no `instructions` prop -- that was a silent
              no-op in the pre-TS JS version. The agent's real instructions
              live server-side in backend/app/agents/curriculum/agent.py. */}
          <CopilotChat agentId="curriculum_team" />
        </div>
      </div>
    );
  }

  return (
    <div className="home-hub">
      <div className="home-prompt-section">
        <h2>What will you build today?</h2>
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
