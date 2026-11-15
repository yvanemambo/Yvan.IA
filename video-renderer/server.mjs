import { createServer } from "node:http";
import { createReadStream } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, stat, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomUUID, timingSafeEqual } from "node:crypto";
import { render, check, snapshot, findChrome } from "givemotion";
import { buildComposition } from "./composition.mjs";
import { canvasForAspect, assertRenderDimensions } from "./layout.mjs";

const PORT = Number(process.env.PORT || 10000);
const TOKEN = process.env.VIDEO_RENDERER_TOKEN || "";
const ROOT = process.env.VIDEO_RENDERER_DATA || join(tmpdir(), "yvan-ia-video");
const MAX_BODY = 64 * 1024;
const MAX_QUEUE = 5;
const VISUALS = new Set(["orbit", "bars", "product", "device", "burst"]);
const RETENTION_MS = 24 * 60 * 60 * 1000;
const jobs = new Map();
const queue = [];
let busy = false;

const palettes = {
  modern: { bg: "#0b1020", panel: "#151f38", accent: "#9b7cff", secondary: "#64e4d0" },
  luxury: { bg: "#11100e", panel: "#28221a", accent: "#d8b879", secondary: "#f3e8d1" },
  bold: { bg: "#130d12", panel: "#2a1722", accent: "#ff5b6e", secondary: "#ffd166" },
  minimal: { bg: "#101820", panel: "#1d2a32", accent: "#f0f2f4", secondary: "#8fc8d8" },
  neon: { bg: "#090b18", panel: "#17182e", accent: "#66f2ff", secondary: "#ff6de6" },
};

function json(res, status, data) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
  res.end(JSON.stringify(data));
}
function authorized(req) {
  if (!TOKEN) return false;
  const supplied = req.headers.authorization || "";
  const expected = "Bearer " + TOKEN;
  const a = Buffer.from(supplied);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
async function readJson(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY) throw new Error("Requête trop volumineuse.");
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}
function cleanText(value, limit) {
  return typeof value === "string" ? value.replace(/[<>]/g, "").replace(/\s+/g, " ").trim().slice(0, limit) : "";
}
function validate(data) {
  if (!data || typeof data !== "object") throw new Error("Storyboard invalide.");
  const aspect = ["vertical", "horizontal", "square"].includes(data.aspect) ? data.aspect : null;
  const duration = [10, 15, 20].includes(Number(data.duration)) ? Number(data.duration) : null;
  const style = Object.hasOwn(palettes, data.style) ? data.style : null;
  if (!aspect || !duration || !style) throw new Error("Format, durée ou style non reconnu.");
  if (!Array.isArray(data.scenes) || data.scenes.length < 3 || data.scenes.length > 5) throw new Error("Le storyboard doit contenir de 3 à 5 scènes.");
  const scenes = data.scenes.map((scene, index) => ({
    kicker: cleanText(scene?.kicker, 50),
    title: cleanText(scene?.title, 100),
    subtitle: cleanText(scene?.subtitle, 180),
    visual: VISUALS.has(scene?.visual) ? scene.visual : ["orbit", "bars", "product", "device", "burst"][index % 5],
  }));
  if (scenes.some((scene) => !scene.title)) throw new Error("Chaque scène doit avoir un titre.");
  return { title: cleanText(data.title, 100), scenes, aspect, duration, style };
}
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");


async function runJob(job) {
  job.status = "rendering";
  job.progress = { phase: "préparation", done: 0, total: 0 };
  const dir = await mkdtemp(join(ROOT, "job-"));
  job.dir = dir;
  const htmlPath = join(dir, "composition.html");
  const outputPath = join(dir, "yvan-ia-motion.mp4");
  await writeFile(htmlPath, buildComposition(job.storyboard, palettes, canvasForAspect, esc), "utf8");
  const { width, height } = canvasForAspect(job.storyboard.aspect);
  job.progress = { phase: "contrôle qualité", done: 0, total: 0 };
  const quality = await check(htmlPath, { workers: 1, motion: true, pacing: true });
  if (quality.errors > 0) {
    const first = quality.issues.filter((issue) => issue.severity === "error").slice(0, 3).map((issue) => issue.message).join(" | ");
    throw new Error("Contrôle qualité GiveMotion : " + (first || "problème de composition détecté."));
  }
  const result = await render(htmlPath, {
    output: outputPath, quality: "high", motionBlur: "auto", workers: 1, width, height, fps: 30,
    timeoutMs: 120000, hardware: false, cache: false, quiet: true,
    onProgress: (p) => { job.progress = { phase: p.phase, done: p.done || 0, total: p.total || 0, eta: p.eta ?? null }; },
  });
  assertRenderDimensions(result, width, height);
  const probe = spawnSync("ffprobe", ["-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", outputPath], { encoding: "utf8", timeout: 15000 });
  if (probe.error || probe.status !== 0) throw new Error("Impossible de vérifier les dimensions du MP4 final.");
  const stream = JSON.parse(probe.stdout || "{}").streams?.[0];
  assertRenderDimensions(stream, width, height);
  job.progress = { phase: "vérification des scènes", done: 0, total: 0 };
  const review = await snapshot(htmlPath, { output: join(dir, "review"), max: 8, cols: 4, transitions: true, grid: true });
  if (review.errors?.length) throw new Error("La vérification visuelle a détecté une erreur dans les scènes.");
  const info = await stat(outputPath);
  if (!info.size) throw new Error("Le fichier MP4 est vide.");
  job.result = { duration: result.duration, width, height, bytes: info.size, scenes: job.storyboard.scenes.length, quality: { errors: quality.errors, warnings: quality.warnings, motionChecked: Boolean(quality.motion), reviewFrames: review.files?.length || review.times?.length || 0 }, renderQuality: "high" };
  job.outputPath = outputPath;
  job.status = "completed";
  job.progress = { phase: "terminé", done: result.frames, total: result.frames, eta: 0 };
}

async function processQueue() {
  if (busy) return;
  busy = true;
  try {
    while (queue.length) {
      const job = queue.shift();
      try { await runJob(job); }
      catch (error) { job.status = "failed"; job.error = String(error?.message || error).slice(0, 500); }
    }
  } finally { busy = false; }
}
function publicJob(job) {
  return { id: job.id, status: job.status, progress: job.progress, result: job.result || null, error: job.error || null, createdAt: job.createdAt };
}
async function handler(req, res) {
  const url = new URL(req.url, "http://localhost");
  if (req.method === "GET" && url.pathname === "/health") {
    const ffmpeg = spawnSync("ffmpeg", ["-version"], { encoding: "utf8" });
    return json(res, 200, { ok: Boolean(TOKEN && findChrome() && !ffmpeg.error && ffmpeg.status === 0), renderer: "GiveMotion 0.1.6", chrome: Boolean(findChrome()), ffmpeg: !ffmpeg.error && ffmpeg.status === 0, queued: queue.length, busy });
  }
  if (!authorized(req)) return json(res, 401, { error: "Accès au moteur vidéo refusé." });
  if (req.method === "POST" && url.pathname === "/jobs") {
    let data;
    try { data = validate(await readJson(req)); }
    catch (error) { return json(res, 400, { error: error.message || "Storyboard invalide." }); }
    if (queue.length >= MAX_QUEUE) return json(res, 429, { error: "Le studio est occupé. Réessaie dans quelques minutes." });
    const job = { id: randomUUID(), storyboard: data, status: "queued", progress: { phase: "en attente", done: 0, total: 0 }, createdAt: new Date().toISOString(), createdMs: Date.now() };
    jobs.set(job.id, job);
    queue.push(job);
    processQueue();
    return json(res, 202, publicJob(job));
  }
  const match = url.pathname.match(/^\/jobs\/([a-f0-9-]{36})(\/video)?$/);
  if (req.method === "GET" && match) {
    const job = jobs.get(match[1]);
    if (!job) return json(res, 404, { error: "Vidéo introuvable ou expirée." });
    if (match[2]) {
      if (job.status !== "completed" || !job.outputPath) return json(res, 409, { error: "La vidéo n'est pas encore prête." });
      const info = await stat(job.outputPath).catch(() => null);
      if (!info) return json(res, 404, { error: "Le fichier vidéo n'est plus disponible." });
      res.writeHead(200, { "Content-Type": "video/mp4", "Content-Length": info.size, "Content-Disposition": 'attachment; filename="yvan-ia-motion.mp4"', "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
      return createReadStream(job.outputPath).pipe(res);
    }
    return json(res, 200, publicJob(job));
  }
  return json(res, 404, { error: "Route inconnue." });
}

await mkdir(ROOT, { recursive: true });
const server = createServer((req, res) => {
  handler(req, res).catch((error) => {
    if (!res.headersSent) json(res, 500, { error: "Erreur interne du moteur vidéo." });
    else res.destroy(error);
  });
});
server.listen(PORT, "0.0.0.0", () => process.stdout.write(`Yvan.IA GiveMotion renderer listening on ${PORT}\n`));
setInterval(async () => {
  const cutoff = Date.now() - RETENTION_MS;
  for (const [id, job] of jobs) {
    if (job.createdMs < cutoff && job.status !== "rendering") {
      jobs.delete(id);
      if (job.dir) await rm(job.dir, { recursive: true, force: true }).catch(() => {});
    }
  }
}, 60 * 60 * 1000).unref();
