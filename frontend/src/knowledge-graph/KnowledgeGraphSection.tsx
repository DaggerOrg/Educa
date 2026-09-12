// Wraps the Knowledge Graph nav item with a second, collapsible sidebar --
// a ChatGPT-style history of collaborative graph boards (BoardHistorySidebar)
// -- next to the main content. With no board selected, the main content is
// exactly today's KnowledgeGraphPage (the original mock-backed example,
// left untouched); picking or creating a board swaps it for
// LiveKnowledgeGraphCanvas, a realtime multiplayer version of the same
// canvas backed by Liveblocks instead of mock data.
//
// The boards list itself lives here, not in the sidebar, so both the
// sidebar (names/actions) and the canvas (header title) can read it without
// two independent polling loops drifting out of sync.
import { useEffect, useState } from "react";
import { createKgBoard, deleteKgBoard, listKgBoards, renameKgBoard } from "../api.ts";
import type { Session } from "../auth.ts";
import type { KgBoard } from "../types.ts";
import KnowledgeGraphPage from "./KnowledgeGraphPage.tsx";
import BoardHistorySidebar from "./live/BoardHistorySidebar.tsx";
import LiveKnowledgeGraphCanvas from "./live/LiveKnowledgeGraphCanvas.tsx";
import "./styles/knowledge-graph.css";

const POLL_INTERVAL_MS = 5000;

interface KnowledgeGraphSectionProps {
  session: Session;
}

export default function KnowledgeGraphSection({ session }: KnowledgeGraphSectionProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);
  const [boards, setBoards] = useState<KgBoard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    function refresh() {
      listKgBoards()
        .then((data) => { if (!cancelled) { setBoards(data); setError(null); } })
        .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    }
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  async function handleCreate(title: string) {
    const board = await createKgBoard(title);
    setBoards((prev) => (prev ? [board, ...prev] : [board]));
    setSelectedBoardId(board.id);
  }

  async function handleRename(board: KgBoard, title: string) {
    const updated = await renameKgBoard(board.id, title);
    setBoards((prev) => prev?.map((b) => (b.id === board.id ? updated : b)) ?? null);
  }

  async function handleDelete(board: KgBoard) {
    await deleteKgBoard(board.id);
    setBoards((prev) => prev?.filter((b) => b.id !== board.id) ?? null);
    if (selectedBoardId === board.id) setSelectedBoardId(null);
  }

  const selectedBoard = boards?.find((b) => b.id === selectedBoardId) ?? null;

  return (
    <div className="kg-section">
      <BoardHistorySidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((v) => !v)}
        boards={boards}
        error={error}
        selectedBoardId={selectedBoardId}
        onSelectBoard={setSelectedBoardId}
        onCreate={handleCreate}
        onRename={handleRename}
        onDelete={handleDelete}
      />
      <div className="kg-section-main">
        {selectedBoard ? (
          <LiveKnowledgeGraphCanvas key={selectedBoard.id} session={session} board={selectedBoard} />
        ) : (
          <KnowledgeGraphPage />
        )}
      </div>
    </div>
  );
}
