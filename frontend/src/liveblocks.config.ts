// Shared types for every Liveblocks-backed feature in Studio: the lecturers'
// chat (Feeds -- see components/TeacherChat.tsx) and the collaborative
// knowledge-graph boards (Storage, via @liveblocks/react-flow -- see
// knowledge-graph/live/). `UserMeta` mirrors what backend/app/
// liveblocks_auth.py sets as `userInfo` when minting a token -- `color` is
// used by @liveblocks/react-flow's `Cursors` for each teacher's live cursor.
declare global {
  interface Liveblocks {
    UserMeta: {
      id: string;
      info: {
        name: string;
        color: string;
      };
    };
    FeedMessageData: {
      userId: string;
      name: string;
      content: string;
      courseTitle: string | null;
    };
    FeedMetadata: Record<string, never>;
  }
}

export {};
