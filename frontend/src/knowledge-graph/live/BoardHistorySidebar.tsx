// A ChatGPT-style history list of collaborative knowledge-graph boards --
// the second, collapsible panel on the Knowledge Graph page (see
// KnowledgeGraphSection.tsx, which owns the actual board list/polling).
// Shared across every teacher, like the lecturers' chat: anyone can create
// a board, open it, and co-edit live.
import { useState } from "react";
import type { KgBoard } from "../../types.ts";
import { IconChevronLeft, IconClose, IconEdit, IconPlus } from "../../components/icons.tsx";

interface BoardHistorySidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  boards: KgBoard[] | null;
  error: string | null;
  selectedBoardId: string | null;
  onSelectBoard: (boardId: string | null) => void;
  onCreate: (title: string) => Promise<void>;
  onRename: (board: KgBoard, title: string) => Promise<void>;
  onDelete: (board: KgBoard) => Promise<void>;
}

export default function BoardHistorySidebar({
  collapsed, onToggleCollapsed, boards, error, selectedBoardId, onSelectBoard, onCreate, onRename, onDelete,
}: BoardHistorySidebarProps) {
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleNewBoard() {
    const title = window.prompt("Name this knowledge graph", "Untitled graph");
    if (!title) return;
    try {
      await onCreate(title);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleRename(board: KgBoard, e: React.MouseEvent) {
    e.stopPropagation();
    const title = window.prompt("Rename this knowledge graph", board.title);
    if (!title || title === board.title) return;
    try {
      await onRename(board, title);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleDelete(board: KgBoard, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm(`Delete "${board.title}"? This can't be undone.`)) return;
    try {
      await onDelete(board);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    }
  }

  if (collapsed) {
    return (
      <div className="kg-history kg-history-collapsed">
        <button type="button" className="kg-history-toggle" title="Expand history" onClick={onToggleCollapsed}>
          <IconChevronLeft className="kg-history-toggle-icon is-collapsed" />
        </button>
      </div>
    );
  }

  return (
    <div className="kg-history">
      <div className="kg-history-head">
        <span className="field-label">Live graphs</span>
        <button type="button" className="kg-history-toggle" title="Collapse history" onClick={onToggleCollapsed}>
          <IconChevronLeft className="kg-history-toggle-icon" />
        </button>
      </div>

      <button type="button" className="btn btn-primary kg-history-new" onClick={handleNewBoard}>
        <IconPlus /> New graph
      </button>

      {(error || actionError) && <div className="error-banner kg-history-error">{error || actionError}</div>}

      <div className="kg-history-list">
        {boards === null ? (
          <p className="hint">Loading…</p>
        ) : boards.length === 0 ? (
          <p className="hint kg-history-empty">No live graphs yet — start one.</p>
        ) : (
          boards.map((board) => (
            <button
              type="button"
              key={board.id}
              className={`kg-history-item${selectedBoardId === board.id ? " is-active" : ""}`}
              onClick={() => onSelectBoard(board.id)}
            >
              <span className="kg-history-item-title">{board.title}</span>
              <span className="kg-history-item-meta">by {board.createdByName}</span>
              <span className="kg-history-item-actions">
                <span className="kg-history-item-action" onClick={(e) => handleRename(board, e)} title="Rename">
                  <IconEdit />
                </span>
                <span className="kg-history-item-action" onClick={(e) => handleDelete(board, e)} title="Delete">
                  <IconClose />
                </span>
              </span>
            </button>
          ))
        )}
      </div>

      {selectedBoardId && (
        <button type="button" className="btn kg-history-back" onClick={() => onSelectBoard(null)}>
          Back to example graph
        </button>
      )}
    </div>
  );
}
