// Card footprint used to bound a set of node positions. Cards are a fixed
// 200px wide (.kg-node); height varies with a wrapped name, so a typical
// two-line card is assumed.
const NODE_W = 200;
const NODE_H = 80;
const PAD = 32;

interface Options {
  // Room to leave along the top edge for whatever floats over the canvas.
  top: number;
  // Never zoom out past this; past it, the top-left of the graph is anchored
  // instead of centering a crop that cuts nodes in half.
  minZoom: number;
}

export function viewportFor(
  positions: { x: number; y: number }[],
  size: { width: number; height: number },
  { top, minZoom }: Options,
) {
  const minX = Math.min(...positions.map((p) => p.x));
  const minY = Math.min(...positions.map((p) => p.y));
  const w = Math.max(...positions.map((p) => p.x)) + NODE_W - minX;
  const h = Math.max(...positions.map((p) => p.y)) + NODE_H - minY;
  const availW = size.width - 2 * PAD;
  const availH = size.height - top - PAD;
  const fit = Math.min(availW / w, availH / h, 1);
  const zoom = Math.max(fit, minZoom);
  const fits = fit >= minZoom;
  return {
    zoom,
    x: fits ? PAD + (availW - w * zoom) / 2 - minX * zoom : PAD - minX * zoom,
    y: fits ? top + (availH - h * zoom) / 2 - minY * zoom : top - minY * zoom,
  };
}
