import { Component, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ClientSideSuspense,
  LiveblocksProvider,
  RoomProvider,
  useCreateFeed,
  useCreateFeedMessage,
  useFeedMessages,
  useSelf,
} from "@liveblocks/react/suspense";
import "../liveblocks.config.ts";
import { API_BASE } from "../api.ts";
import type { Session } from "../auth.ts";
import type { Course } from "../types.ts";
import { IconChat } from "./icons.tsx";

// Every lecturer shares this one Liveblocks room/feed -- see the "shared
// staff room" scope decision (no co-teacher/collaborator model exists yet,
// so a room per course would only ever be visible to that course's single
// owner). backend/app/liveblocks_auth.py grants every authenticated teacher
// the same fixed write permission on this room id.
const ROOM_ID = "lecturers-chat";
const FEED_ID = "general";

interface TeacherChatProps {
  session: Session;
  courses: Course[];
}

export default function TeacherChat({ session, courses }: TeacherChatProps) {
  // `room` is undefined for notification-only tokens; this app always
  // connects to ROOM_ID, but the callback still needs to match the
  // `authEndpoint` signature Liveblocks calls.
  const authEndpoint = useCallback(
    async () => {
      const res = await fetch(`${API_BASE}/liveblocks-auth`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({ room: ROOM_ID }),
      });
      if (!res.ok) throw new Error("Couldn't authorize the chat connection");
      return await res.json();
    },
    [session.token],
  );

  return (
    <ChatErrorBoundary>
      <LiveblocksProvider authEndpoint={authEndpoint}>
        <RoomProvider id={ROOM_ID}>
          <ClientSideSuspense fallback={<TeacherChatShell><p className="hint">Loading…</p></TeacherChatShell>}>
            <ChatRoom courses={courses} />
          </ClientSideSuspense>
        </RoomProvider>
      </LiveblocksProvider>
    </ChatErrorBoundary>
  );
}

function TeacherChatShell({ children }: { children: ReactNode }) {
  return (
    <div className="teacher-chat">
      <div className="teacher-chat-head">
        <h2><IconChat /> Chat</h2>
        <p className="hint">
          One shared room for every lecturer — coordinate on courses, ask for a second opinion,
          flag something that needs review.
        </p>
      </div>
      {children}
    </div>
  );
}

interface ChatRoomProps {
  courses: Course[];
}

function ChatRoom({ courses }: ChatRoomProps) {
  const { messages } = useFeedMessages(FEED_ID);
  const createFeed = useCreateFeed();
  const createFeedMessage = useCreateFeedMessage();
  const self = useSelf();
  const [draft, setDraft] = useState("");
  const [courseTitle, setCourseTitle] = useState("");
  const listRef = useRef<HTMLDivElement | null>(null);
  // Only auto-scroll to new messages if the reader was already at the
  // bottom -- otherwise a live update mid-scrollback would yank them down.
  const atBottomRef = useRef(true);
  // A feed must exist before its first message is added ("Feed general not
  // found" otherwise) -- if there are already messages, someone else has
  // created it, so this only fires for the very first message in the room.
  const feedEnsured = useRef(messages.length > 0);

  const sorted = useMemo(() => [...messages].sort((a, b) => a.createdAt - b.createdAt), [messages]);

  useEffect(() => {
    const el = listRef.current;
    if (el && atBottomRef.current) el.scrollTop = el.scrollHeight;
  }, [sorted.length]);

  function handleScroll() {
    const el = listRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
  }

  async function sendMessage() {
    const content = draft.trim();
    if (!content) return;
    if (!feedEnsured.current) {
      feedEnsured.current = true;
      try {
        await createFeed(FEED_ID, {});
      } catch {
        // Someone else created it first between our check and this call --
        // that's fine, the feed exists either way.
      }
    }
    createFeedMessage(FEED_ID, {
      userId: self.id,
      name: self.info.name,
      content,
      courseTitle: courseTitle || null,
    });
    setDraft("");
    atBottomRef.current = true;
  }

  return (
    <TeacherChatShell>
      <div className="teacher-chat-messages" ref={listRef} onScroll={handleScroll}>
        {sorted.length === 0 ? (
          <p className="hint teacher-chat-empty">No messages yet — say hello.</p>
        ) : (
          sorted.map((message) => (
            <div className={`chat-message${message.data.userId === self.id ? " is-own" : ""}`} key={message.id}>
              <div className="chat-message-meta">
                <span className="chat-message-author">
                  {message.data.userId === self.id ? "You" : message.data.name}
                </span>
                <span>{formatTimestamp(message.createdAt)}</span>
                {message.data.courseTitle && (
                  <span className="chat-message-course-tag">{message.data.courseTitle}</span>
                )}
              </div>
              <p className="chat-message-body">{message.data.content}</p>
            </div>
          ))
        )}
      </div>

      <form
        className="teacher-chat-composer"
        onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
      >
        <div className="teacher-chat-composer-row">
          {courses.length > 0 && (
            <select
              className="teacher-chat-course-select"
              value={courseTitle}
              onChange={(e) => setCourseTitle(e.target.value)}
              title="Tag a course this message is about (optional)"
            >
              <option value="">No course tag</option>
              {courses.map((c) => (
                <option key={c.id} value={c.title}>{c.title}</option>
              ))}
            </select>
          )}
          <textarea
            className="teacher-chat-textarea"
            placeholder="Message other lecturers…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            rows={1}
          />
          <button type="submit" className="btn btn-primary teacher-chat-send" disabled={!draft.trim()}>
            Send
          </button>
        </div>
      </form>
    </TeacherChatShell>
  );
}

function formatTimestamp(ms: number): string {
  const date = new Date(ms);
  const now = new Date();
  const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (date.toDateString() === now.toDateString()) return time;
  return `${date.toLocaleDateString([], { month: "short", day: "numeric" })} ${time}`;
}

interface ChatErrorBoundaryState {
  error: Error | null;
}

// Liveblocks' Suspense hooks throw to the nearest error boundary (there's no
// non-throwing way to surface e.g. a failed auth call) -- without this, a
// misconfigured LIVEBLOCKS_API_KEY would blank the whole Studio app, not
// just this panel.
class ChatErrorBoundary extends Component<{ children: ReactNode }, ChatErrorBoundaryState> {
  state: ChatErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ChatErrorBoundaryState {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <TeacherChatShell>
          <div className="error-banner teacher-chat-error">
            Couldn't connect to chat: {this.state.error.message}
          </div>
        </TeacherChatShell>
      );
    }
    return this.props.children;
  }
}
