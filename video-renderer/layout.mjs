export const CANVAS_SIZES = Object.freeze({
  vertical: Object.freeze({ width: 1080, height: 1920 }),
  horizontal: Object.freeze({ width: 1920, height: 1080 }),
  square: Object.freeze({ width: 1080, height: 1080 }),
});
export function canvasForAspect(aspect) {
  const canvas = CANVAS_SIZES[aspect];
  if (!canvas) throw new Error("Format vidéo non reconnu.");
  return canvas;
}
export function assertRenderDimensions(actual, width, height) {
  const actualWidth = Number(actual?.width);
  const actualHeight = Number(actual?.height);
  if (actualWidth !== width || actualHeight !== height) {
    throw new Error(`Dimensions vidéo incorrectes : attendu ${width}x${height}, reçu ${actualWidth || "?"}x${actualHeight || "?"}.`);
  }
  return true;
}
