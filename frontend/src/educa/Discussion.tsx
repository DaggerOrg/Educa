import { useEffect, useState } from "react";
import type { Session } from "../auth.ts";
import { addPost, getPosts, type ForumPost } from "./traditionalData.ts";

interface DiscussionProps {
  courseId: string;
  lessonId: string;
  lessonTitle: string;
  session: Session;
}

export default function Discussion({ courseId, lessonId, lessonTitle, session }: DiscussionProps) {
  const [posts, setPosts] = useState<ForumPost[]>([]);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    setPosts(getPosts(courseId, lessonId, lessonTitle));
    setDraft("");
  }, [courseId, lessonId, lessonTitle]);

  function handlePost() {
    if (!draft.trim()) return;
    setPosts(addPost(courseId, lessonId, lessonTitle, session.user.id, session.user.name, session.user.role, draft.trim()));
    setDraft("");
  }

  return (
    <div className="forum-block">
      <label className="field-label">Discussion</label>
      {posts.length === 0 ? (
        <p className="hint">No posts yet — be the first to ask a question.</p>
      ) : (
        <ul className="forum-post-list">
          {posts.map((p) => (
            <li className="forum-post" key={p.id}>
              <div className="forum-post-head">
                <strong>{p.authorName}</strong>
                <span className={`status-pill ${p.authorRole === "teacher" ? "status-approved" : "status-draft"}`}>
                  {p.authorRole}
                </span>
                <span className="hint-inline">{new Date(p.createdAt).toLocaleString()}</span>
              </div>
              <p>{p.body}</p>
            </li>
          ))}
        </ul>
      )}
      <div className="forum-composer">
        <textarea rows={2} value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Ask a question or share a thought…" />
        <button type="button" className="btn" disabled={!draft.trim()} onClick={handlePost}>Post</button>
      </div>
    </div>
  );
}
