import test from "node:test";
import assert from "node:assert/strict";
import { canvasForAspect, assertRenderDimensions } from "./layout.mjs";
test("vertical canvas is exact 9:16", () => assert.deepEqual(canvasForAspect("vertical"), { width: 1080, height: 1920 }));
test("horizontal canvas is exact 16:9", () => assert.deepEqual(canvasForAspect("horizontal"), { width: 1920, height: 1080 }));
test("square canvas is exact 1:1", () => assert.deepEqual(canvasForAspect("square"), { width: 1080, height: 1080 }));
test("unknown aspect is rejected", () => assert.throws(() => canvasForAspect("panorama"), /Format vidéo non reconnu/));
test("render output dimensions must match requested canvas", () => {
  assert.equal(assertRenderDimensions({ width: 1080, height: 1920 }, 1080, 1920), true);
  assert.throws(() => assertRenderDimensions({ width: 1920, height: 1080 }, 1080, 1920), /Dimensions vidéo incorrectes/);
});
