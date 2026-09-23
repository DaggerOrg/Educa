import { useState } from "react";
import { IconSearch } from "../../../components/icons.tsx";
import { NODE_TYPE_LABELS } from "../../types/knowledgeGraph.ts";
import type { KnowledgeNode } from "../../types/knowledgeGraph.ts";

interface GraphSearchProps {
  query: string;
  onQueryChange: (q: string) => void;
  results: KnowledgeNode[];
  onSelectResult: (nodeId: string) => void;
}

export default function GraphSearch({ query, onQueryChange, results, onSelectResult }: GraphSearchProps) {
  const [focused, setFocused] = useState(false);
  const showResults = focused && query.trim().length > 0;

  return (
    <div className="kg-search marketplace-search">
      <IconSearch className="marketplace-search-icon" />
      <input
        type="search"
        className="auth-input marketplace-search-input"
        placeholder="Search the graph — e.g. “present perfect”"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setTimeout(() => setFocused(false), 120)}
      />
      {showResults && (
        <div className="kg-search-results">
          {results.length === 0 ? (
            <div className="kg-search-empty hint">No matches.</div>
          ) : (
            results.map((n) => (
              <button
                type="button"
                key={n.id}
                className="kg-search-result"
                onMouseDown={() => onSelectResult(n.id)}
              >
                <span className="kg-search-result-name">{n.name}</span>
                <span className="kg-search-result-type">{NODE_TYPE_LABELS[n.type]}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
