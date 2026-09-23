// A ChatGPT-style history list of collaborative knowledge-graph boards --
// the second, collapsible panel on the Knowledge Graph page (see
// KnowledgeGraphSection.tsx, which owns the actual board list/polling).
// Shared across every teacher, like the lecturers' chat: anyone can create
// a board, open it, and co-edit live.
import { useState } from "react";
import type { KgBoard } from "../../types.ts";
import DeleteConfirmationDialog from "../components/dialogs/DeleteConfirmationDialog.tsx";
import TextPromptDialog from "../components/dialogs/TextPromptDialog.tsx";
import { IconChevronLeft, IconClose, IconEdit, IconGraph, IconPlus } from "../../components/icons.tsx";

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

type Dialog = { kind: "new" } | { kind: "rename"; board: KgBoard } | { kind: "delete"; board: KgBoard } | null;

const EXAMPLE_TITLE = "Example graph";
const EXAMPLE_META = "English B1 · sample";

// "Grammar Unit 3" -> "GU", "Untitled" -> "UN": what a board's chip shows when the panel is collapsed.
function initials(title: string): string {
  const words = title.trim().split(/\s+/).filter(Boolean);
  const letters = words.length > 1 ? [Array.from(words[0])[0], Array.from(words[1])[0]] : Array.from(words[0] ?? "?").slice(0, 2);
  return letters.join("").toUpperCase();
}

export default function BoardHistorySidebar({
  collapsed, onToggleCollapsed, boards, error, selectedBoardId, onSelectBoard, onCreate, onRename, onDelete,
}: BoardHistorySidebarProps) {
  const [actionError, setActionError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<Dialog>(null);

  function openRename(board: KgBoard, e: React.MouseEvent) {
    e.stopPropagation();
    setDialog({ kind: "rename", board });
  }

  function openDelete(board: KgBoard, e: React.MouseEvent) {
    e.stopPropagation();
    setDialog({ kind: "delete", board });
  }

  return (
    <div className={`kg-history${collapsed ? " kg-history-collapsed" : ""}`}>
      {collapsed ? (
        <>
          <button type="button" className="kg-history-toggle" title="Expand live graphs" aria-label="Expand live graphs" onClick={onToggleCollapsed}>
            <IconChevronLeft className="kg-history-toggle-icon is-collapsed" />
          </button>
          <button type="button" className="kg-rail-new" title="New graph" aria-label="New graph" onClick={() => setDialog({ kind: "new" })}>
            <IconPlus />
          </button>
          <div className="kg-rail-divider" />
          <div className="kg-rail-list">
            <button
              type="button"
              className={`kg-rail-chip${selectedBoardId === null ? " is-active" : ""}`}
              title={`${EXAMPLE_TITLE} — ${EXAMPLE_META}`}
              aria-label={EXAMPLE_TITLE}
              aria-pressed={selectedBoardId === null}
              onClick={() => onSelectBoard(null)}
            >
              <IconGraph />
            </button>
            {boards === null ? (
              <span className="kg-rail-loading" aria-label="Loading live graphs">…</span>
            ) : (
              boards.map((board) => (
                <button
                  type="button"
                  key={board.id}
                  className={`kg-rail-chip${selectedBoardId === board.id ? " is-active" : ""}`}
                  title={`${board.title} — by ${board.createdByName}`}
                  aria-label={board.title}
                  aria-pressed={selectedBoardId === board.id}
                  onClick={() => onSelectBoard(board.id)}
                >
                  {initials(board.title)}
                </button>
              ))
            )}
          </div>
        </>
      ) : (
        <>
          <div className="kg-history-head">
            <span className="field-label">Live graphs</span>
            <button type="button" className="kg-history-toggle" title="Collapse live graphs" aria-label="Collapse live graphs" onClick={onToggleCollapsed}>
              <IconChevronLeft className="kg-history-toggle-icon" />
            </button>
          </div>

          <button type="button" className="btn btn-primary kg-history-new" onClick={() => setDialog({ kind: "new" })}>
            <IconPlus /> New graph
          </button>

          {(error || actionError) && <div className="error-banner kg-history-error">{error || actionError}</div>}

          <div className="kg-history-list">
            <button
              type="button"
              className={`kg-history-item${selectedBoardId === null ? " is-active" : ""}`}
              onClick={() => onSelectBoard(null)}
            >
              <span className="kg-history-item-title">{EXAMPLE_TITLE}</span>
              <span className="kg-history-item-meta">{EXAMPLE_META}</span>
            </button>
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
                    <span className="kg-history-item-action" onClick={(e) => openRename(board, e)} title="Rename">
                      <IconEdit />
                    </span>
                    <span className="kg-history-item-action" onClick={(e) => openDelete(board, e)} title="Delete">
                      <IconClose />
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        </>
      )}

      {dialog?.kind === "new" && (
        <TextPromptDialog
          title="New knowledge graph"
          label="Name"
          initialValue="Untitled graph"
          submitLabel="Create"
          onCancel={() => setDialog(null)}
          onSubmit={async (title) => {
            await onCreate(title);
            setDialog(null);
          }}
        />
      )}
      {dialog?.kind === "rename" && (
        <TextPromptDialog
          title="Rename knowledge graph"
          label="Name"
          initialValue={dialog.board.title}
          submitLabel="Rename"
          onCancel={() => setDialog(null)}
          onSubmit={async (title) => {
            if (title !== dialog.board.title) await onRename(dialog.board, title);
            setDialog(null);
          }}
        />
      )}
      {dialog?.kind === "delete" && (
        <DeleteConfirmationDialog
          title="Delete graph"
          description={`Delete "${dialog.board.title}"? This can't be undone.`}
          onCancel={() => setDialog(null)}
          onConfirm={async () => {
            try {
              await onDelete(dialog.board);
            } catch (e) {
              setActionError(e instanceof Error ? e.message : String(e));
            }
            setDialog(null);
          }}
        />
      )}
    </div>
  );
}
