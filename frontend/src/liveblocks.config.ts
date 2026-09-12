// Types for the lecturers' chat (Liveblocks Feeds) -- see
// components/TeacherChat.tsx. `UserMeta` mirrors what backend/app/
// liveblocks_auth.py sets as `userInfo` when minting a token; `FeedMessageData`
// is the JSON shape of every message stored in the feed.
declare global {
  interface Liveblocks {
    UserMeta: {
      id: string;
      info: {
        name: string;
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
