import { useMemo } from "react";
import { neighborhoodOf, type GraphLink, type Neighborhood } from "../utils/neighborhood.ts";

// Focus mode's view of the graph: the selected node with what leads into it and
// what it leads to. `centerId` is null when Focus is off (or nothing suitable is
// selected), which gives null back. `links` should be memoized by the caller.
export function useFocusView(centerId: string | null, links: GraphLink[]): Neighborhood | null {
  return useMemo(() => (centerId ? neighborhoodOf(centerId, links) : null), [centerId, links]);
}
