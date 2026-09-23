import { useState } from "react";

// Two ways to read the same graph: the canvas, or a top-to-bottom list from
// the basics to the advanced (utils/learningPath.ts). Both are remembered on
// this device, and shared by the example graph and the live boards.
export type GraphView = "graph" | "path";
// "down": basics at the top. "up": basics at the bottom, climbing to the advanced at the top.
export type PathDirection = "down" | "up";

const VIEW_KEY = "educa_kg_view";
const DIRECTION_KEY = "educa_kg_path_direction";

function usePersisted<T extends string>(key: string, allowed: readonly T[], fallback: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return allowed.find((v) => v === stored) ?? fallback;
    } catch {
      return fallback;
    }
  });
  function update(next: T) {
    setValue(next);
    try {
      localStorage.setItem(key, next);
    } catch {
      // The choice just won't outlast this session.
    }
  }
  return [value, update];
}

export const useGraphView = () => usePersisted<GraphView>(VIEW_KEY, ["graph", "path"], "graph");
export const usePathDirection = () => usePersisted<PathDirection>(DIRECTION_KEY, ["down", "up"], "down");
