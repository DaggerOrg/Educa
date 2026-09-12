import { useCallback, useState } from "react";

export type GraphSelection = { kind: "node"; id: string } | { kind: "relationship"; id: string } | null;

export function useGraphSelection() {
  const [selection, setSelection] = useState<GraphSelection>(null);

  const selectNode = useCallback((id: string) => setSelection({ kind: "node", id }), []);
  const selectRelationship = useCallback((id: string) => setSelection({ kind: "relationship", id }), []);
  const clearSelection = useCallback(() => setSelection(null), []);

  return { selection, selectNode, selectRelationship, clearSelection };
}
