import { createServer } from "node:http";
import { createReadStream } from "node:fs";
import { mkdir, mkdtemp, readFile, rm, stat, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomUUID, timingSafeEqual } from "node:crypto";
import { render, findChrome } from "givemotion";

const PORT = Number(process.env.PORT || 10000);
const TOKEN = process.env.VIDEO_RENDERER_TOKEN || "";
const ROOT = process.env.VIDEO_RENDERER_DATA || join(tmpdir(), "yvan-ia-video");
const MAX_BODY = 64 * 1024;
const MAX_QUEUE = 5;
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
  const scenes = data.scenes.map((scene) => ({
    kicker: cleanText(scene?.kicker, 50),
    title: cleanText(scene?.title, 100),
    subtitle: cleanText(scene?.subtitle, 180),
  }));
  if (scenes.some((scene) => !scene.title)) throw new Error("Chaque scène doit avoir un titre.");
  return { title: cleanText(data.title, 100), scenes, aspect, duration, style };
}
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

function buildComposition(data) {
  const theme = palettes[data.style];
  const sizes = data.aspect === "vertical" ? [1080, 1920] : data.aspect === "horizontal" ? [1920, 1080] : [1080, 1080];
  const sceneDuration = (data.duration + (data.scenes.length - 1) * 0.5) / data.scenes.length;
  const scenes = data.scenes.map((scene, index) => {
    const kicker = scene.kicker || data.title || "YVAN.IA STUDIO";
    const subtitle = scene.subtitle || "";
    return `
      <section class="scene" data-duration="${sceneDuration.toFixed(2)}">
        <div class="glow glow-a"></div><div class="glow glow-b"></div>
        <div class="frame">
          <div class="topline"><span>YVAN.IA / MOTION</span><span>0${index + 1} — 0${data.scenes.length}</span></div>
          <div class="copy">
            <p class="kicker" data-enter="fade-up 0.6 0.15">${esc(kicker)}</p>
            <h1 data-enter="rise 0.85 0.35">${esc(scene.title)}</h1>
            ${subtitle ? `<p class="subtitle" data-enter="fade-up 0.7 0.8">${esc(subtitle)}</p>` : ""}
            <div class="accent-line" data-enter="scale 0.7 0.95"></div>
          </div>
          <div class="bottomline"><span>${esc(data.title || "CRÉATION ORIGINALE")}</span><span>STUDIO CRÉATIF</span></div>
        </div>
        <div class="orbit"></div>
      </section>`;
  }).join("\n");
  return `<!doctype html>
<html lang="fr" data-width="${sizes[0]}" data-height="${sizes[1]}" data-fps="30" data-background="${theme.bg}">
<head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}
body{background:${theme.bg};color:#fff;font-family:Inter,Arial,sans-serif}
.scene{position:relative;width:100%;height:100%;overflow:hidden;display:grid;place-items:center;background:radial-gradient(ellipse at 75% 15%,${theme.panel},transparent 55%),linear-gradient(135deg,${theme.bg},#080a12)}
.frame{position:relative;z-index:3;width:84%;height:84%;display:flex;flex-direction:column;justify-content:space-between}
.topline,.bottomline{display:flex;justify-content:space-between;gap:20px;color:#ffffff88;font-size:18px;letter-spacing:.18em;font-weight:700}
.copy{max-width:100%;padding:7% 0}
.kicker{font-size:clamp(20px,2.8vw,34px);letter-spacing:.22em;text-transform:uppercase;color:${theme.secondary};font-weight:800;margin:0 0 38px}
h1{font-size:clamp(70px,10vw,150px);line-height:.96;letter-spacing:-.055em;font-weight:850;margin:0;max-width:100%;overflow-wrap:anywhere}
.subtitle{font-size:clamp(26px,3.5vw,48px);line-height:1.25;color:#e5e8f0;margin:44px 0 0;max-width:90%}
.accent-line{width:180px;height:9px;border-radius:10px;background:linear-gradient(90deg,${theme.accent},${theme.secondary});margin-top:52px;transform-origin:left}
.glow{position:absolute;width:58%;aspect-ratio:1;border-radius:50%;filter:blur(100px);opacity:.18}
.glow-a{background:${theme.accent};right:-18%;top:-25%;animation:float 7s ease-in-out infinite alternate}
.glow-b{background:${theme.secondary};left:-28%;bottom:-30%;animation:float 9s ease-in-out infinite alternate-reverse}
.orbit{position:absolute;z-index:1;width:52%;aspect-ratio:1;border:1px solid #ffffff18;border-radius:50%;right:-20%;bottom:-24%;box-shadow:0 0 0 38px #ffffff08,0 0 0 76px #ffffff05}
@keyframes float{from{transform:translate3d(-3%,-2%,0) scale(.92)}to{transform:translate3d(4%,5%,0) scale(1.08)}}
@media (max-aspect-ratio:1/1){.frame{width:82%;height:86%}.topline,.bottomline{font-size:14px}.kicker{font-size:26px}h1{font-size:100px}.subtitle{font-size:34px}}
</style></head>
<body><main data-sequence data-transition="push-left 0.5">${scenes}</main></body></html>`;
}

async function runJob(job) {
  job.status = "rendering";
  job.progress = { phase: "préparation", done: 0, total: 0 };
  const dir = await mkdtemp(join(ROOT, "job-"));
  job.dir = dir;
  const htmlPath = join(dir, "composition.html");
  const outputPath = join(dir, "yvan-ia-motion.mp4");
  await writeFile(htmlPath, buildComposition(job.storyboard), "utf8");
  const [width, height] = job.storyboard.aspect === "vertical" ? [1080, 1920] : job.storyboard.aspect === "horizontal" ? [1920, 1080] : [1080, 1080];
  const result = await render(htmlPath, {
    output: outputPath, quality: "standard", workers: 1, width, height, fps: 30,
    timeoutMs: 120000, hardware: false, cache: false, quiet: true,
    onProgress: (p) => { job.progress = { phase: p.phase, done: p.done || 0, total: p.total || 0, eta: p.eta ?? null }; },
  });
  const info = await stat(outputPath);
  job.result = { duration: result.duration, width: result.width, height: result.height, bytes: info.size };
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
