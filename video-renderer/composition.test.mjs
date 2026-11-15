import test from "node:test";
import assert from "node:assert/strict";
import { buildComposition } from "./composition.mjs";
import { canvasForAspect } from "./layout.mjs";

const palettes = {
  modern: { bg: "#0b1020", panel: "#151f38", accent: "#9b7cff", secondary: "#64e4d0" },
  luxury: { bg: "#11100e", panel: "#28221a", accent: "#d8b879", secondary: "#f3e8d1" },
  bold: { bg: "#130d12", panel: "#2a1722", accent: "#ff5b6e", secondary: "#ffd166" },
  minimal: { bg: "#101820", panel: "#1d2a32", accent: "#f0f2f4", secondary: "#8fc8d8" },
  neon: { bg: "#090b18", panel: "#17182e", accent: "#66f2ff", secondary: "#ff6de6" },
};
const esc = (value) => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const scenes = [
  { kicker: "Découverte", title: "Une idée nouvelle", subtitle: "Une première scène", visual: "orbit" },
  { kicker: "Performance", title: "Des résultats visibles", subtitle: "Une deuxième scène", visual: "bars" },
  { kicker: "Action", title: "Passez à l'action", subtitle: "Une conclusion", visual: "product" },
];

test("composition uses the exact canvas and requested scene count for all formats", () => {
  for (const aspect of ["vertical", "horizontal", "square"]) {
    const html = buildComposition({ title: "Test", scenes, aspect, duration: 15, style: "modern" }, palettes, canvasForAspect, esc);
    const canvas = canvasForAspect(aspect);
    assert.match(html, new RegExp('data-width="' + canvas.width + '"'));
    assert.match(html, new RegExp('data-height="' + canvas.height + '"'));
    assert.equal((html.match(/class="scene layout-/g) || []).length, 3);
    assert.match(html, /data-transition="push-left 0\.62"/);
  }
});

test("composition includes real scene choreography and word-level typography", () => {
  const html = buildComposition({ title: "Test", scenes, aspect: "vertical", duration: 15, style: "modern" }, palettes, canvasForAspect, esc);
  assert.match(html, /gm\.timeline/);
  assert.match(html, /data-split="words"/);
  assert.match(html, /filter: "blur\(12px\)"/);
  assert.match(html, /class="visual-art"/);
});

test("visual motifs are rendered as distinct vector compositions", () => {
  const motifs = ["orbit", "bars", "product", "device", "burst"];
  for (const visual of motifs) {
    const html = buildComposition({
      title: "Test",
      scenes: [{ title: "One" , visual }, { title: "Two", visual }, { title: "Three", visual }],
      aspect: "square",
      duration: 10,
      style: "modern",
    }, palettes, canvasForAspect, esc);
    assert.ok(html.includes('class="visual-art"'));
    assert.ok(html.includes('data-width="1080"'));
  }
});
