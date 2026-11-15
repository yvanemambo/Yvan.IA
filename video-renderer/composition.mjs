const FONT = {
  modern: '"Space Grotesk", Inter, sans-serif',
  luxury: '"Playfair Display", Georgia, serif',
  bold: '"Bebas Neue", Impact, sans-serif',
  minimal: 'Inter, sans-serif',
  neon: '"Space Grotesk", Inter, sans-serif',
};

function visualMarkup(kind, width, height, theme) {
  const cx = Math.round(width * 0.5), cy = Math.round(height * 0.49);
  const u = Math.round(Math.min(width, height) * 0.16);
  const a = theme.accent, b = theme.secondary, bg = theme.bg;
  if (kind === "bars") {
    const values = [0.34, 0.52, 0.43, 0.72, 0.94], parts = [];
    const bw = u * 0.34, gap = u * 0.16, base = cy + u * 0.72;
    values.forEach((v, i) => parts.push('<rect class="chart-bar" x="' + (cx - 1.35*u + i*(bw+gap)) + '" y="' + (base-v*u*1.4) + '" width="' + bw + '" height="' + (v*u*1.4) + '" rx="' + (bw/2) + '" fill="' + (i===4?b:a) + '" opacity="' + (0.42+i*0.1) + '"/>'));
    return '<g class="visual-art">' + parts.join("") + '<path d="M '+(cx-u*1.35)+' '+(cy+u*.15)+' Q '+(cx-u*.5)+' '+(cy-u*.45)+' '+cx+' '+(cy-u*.12)+' T '+(cx+u*1.35)+' '+(cy-u*.8)+'" fill="none" stroke="#fff" stroke-width="'+Math.max(5,u*.035)+'" opacity=".82"/><circle cx="'+(cx+u*1.35)+'" cy="'+(cy-u*.8)+'" r="'+(u*.1)+'" fill="'+b+'"/></g>';
  }
  if (kind === "product") {
    return '<g class="visual-art"><ellipse cx="'+cx+'" cy="'+(cy+u*.92)+'" rx="'+(u*1.42)+'" ry="'+(u*.25)+'" fill="#000" opacity=".32"/><path d="M '+(cx-u)+' '+(cy-u*.55)+' L '+cx+' '+(cy-u*1.08)+' L '+(cx+u)+' '+(cy-u*.55)+' L '+cx+' '+(cy-u*.02)+' Z" fill="'+b+'"/><path d="M '+(cx-u)+' '+(cy-u*.55)+' L '+cx+' '+(cy-u*.02)+' L '+cx+' '+(cy+u*.98)+' L '+(cx-u)+' '+(cy+u*.42)+' Z" fill="'+a+'"/><path d="M '+(cx+u)+' '+(cy-u*.55)+' L '+cx+' '+(cy-u*.02)+' L '+cx+' '+(cy+u*.98)+' L '+(cx+u)+' '+(cy+u*.42)+' Z" fill="'+b+'" opacity=".72"/><path d="M '+(cx-u*.68)+' '+(cy-u*.45)+' L '+(cx-u*.12)+' '+(cy-u*.75)+'" fill="none" stroke="#fff" stroke-width="'+Math.max(5,u*.04)+'"/></g>';
  }
  if (kind === "device") {
    const pw=u*1.36, ph=u*2.25, x=cx-pw/2, y=cy-ph/2;
    return '<g class="visual-art"><rect x="'+x+'" y="'+y+'" width="'+pw+'" height="'+ph+'" rx="'+(u*.2)+'" fill="#0a0d18" stroke="'+b+'" stroke-width="'+Math.max(7,u*.055)+'"/><rect x="'+(x+u*.12)+'" y="'+(y+u*.2)+'" width="'+(pw-u*.24)+'" height="'+(ph-u*.4)+'" rx="'+(u*.1)+'" fill="'+theme.panel+'"/><rect x="'+(x+u*.26)+'" y="'+(y+u*.45)+'" width="'+(pw-u*.52)+'" height="'+(u*.52)+'" rx="'+(u*.08)+'" fill="'+a+'"/><rect x="'+(x+u*.26)+'" y="'+(y+u*1.12)+'" width="'+(pw-u*.52)+'" height="'+(u*.13)+'" rx="'+(u*.06)+'" fill="#fff" opacity=".8"/><rect x="'+(x+u*.26)+'" y="'+(y+u*1.42)+'" width="'+(pw-u*.52)+'" height="'+(u*.1)+'" rx="'+(u*.05)+'" fill="#fff" opacity=".4"/><rect x="'+(x+u*.26)+'" y="'+(y+u*1.72)+'" width="'+(pw*.48)+'" height="'+(u*.28)+'" rx="'+(u*.08)+'" fill="'+b+'"/></g>';
  }
  if (kind === "burst") {
    const points=[];
    for(let i=0;i<16;i++){const angle=-Math.PI/2+i*Math.PI/8, radius=i%2?u*.72:u*1.5;points.push((cx+Math.cos(angle)*radius).toFixed(1)+","+(cy+Math.sin(angle)*radius).toFixed(1));}
    return '<g class="visual-art"><circle cx="'+cx+'" cy="'+cy+'" r="'+(u*1.55)+'" fill="'+a+'" opacity=".12"/><polygon points="'+points.join(" ")+'" fill="'+a+'"/><circle cx="'+cx+'" cy="'+cy+'" r="'+(u*.48)+'" fill="'+bg+'" stroke="'+b+'" stroke-width="'+Math.max(8,u*.06)+'"/><path d="M '+(cx-u*.2)+' '+cy+' L '+(cx-u*.03)+' '+(cy+u*.18)+' L '+(cx+u*.28)+' '+(cy-u*.2)+'" fill="none" stroke="#fff" stroke-width="'+Math.max(8,u*.07)+'"/></g>';
  }
  return '<g class="visual-art"><circle cx="'+cx+'" cy="'+cy+'" r="'+(u*1.25)+'" fill="'+a+'" opacity=".12"/><circle class="orbit-ring" cx="'+cx+'" cy="'+cy+'" r="'+(u*1.38)+'" fill="none" stroke="'+b+'" stroke-width="'+Math.max(7,u*.045)+'" opacity=".72"/><circle class="orbit-ring" cx="'+cx+'" cy="'+cy+'" r="'+(u*.92)+'" fill="none" stroke="#fff" stroke-width="'+Math.max(4,u*.025)+'" opacity=".34"/><circle cx="'+cx+'" cy="'+cy+'" r="'+(u*.58)+'" fill="'+a+'"/><circle cx="'+(cx-u*.17)+'" cy="'+(cy-u*.17)+'" r="'+(u*.13)+'" fill="#fff"/><circle class="orbit-satellite" cx="'+(cx+u*1.38)+'" cy="'+cy+'" r="'+(u*.13)+'" fill="'+b+'"/></g>';
}

export function buildComposition(data, palettes, canvasForAspect, esc) {
  const theme = palettes[data.style];
  const size = canvasForAspect(data.aspect);
  const width = size.width, height = size.height;
  const transition = 0.62;
  const sceneDuration = (data.duration + (data.scenes.length - 1) * transition) / data.scenes.length;
  const scenes = data.scenes.map((scene, index) => {
    const visual = visualMarkup(scene.visual, width, height, theme);
    const kicker = scene.kicker || data.title || "YVAN.IA STUDIO";
    const subtitle = scene.subtitle || "";
    return '<section class="scene layout-' + data.aspect + '" id="scene-' + index + '" data-duration="' + sceneDuration.toFixed(3) + '" data-camera="push 1.035">' +
      '<div class="glow glow-a"></div><div class="glow glow-b"></div><div class="scene-grid"></div>' +
      '<div class="frame"><div class="visual"><svg viewBox="0 0 ' + width + ' ' + height + '" role="presentation" aria-hidden="true">' + visual + '</svg><span class="visual-label">YVAN.IA · CREATIVE STUDIO</span></div>' +
      '<div class="copy"><p class="kicker">' + esc(kicker) + '</p>' +
      '<h1 class="headline" data-split="words" data-stagger="0.055">' + esc(scene.title) + '</h1>' +
      (subtitle ? '<p class="subtitle" data-split="words" data-stagger="0.035">' + esc(subtitle) + '</p>' : '') +
      '<div class="accent-line"></div><div class="scene-index"><span>0' + (index+1) + '</span><i></i><span>0' + data.scenes.length + '</span></div></div></div></section>';
  }).join("\n");
  const choreography = data.scenes.map((scene, index) => {
    const scope = "#scene-" + index;
    const d = Math.max(1.4, sceneDuration).toFixed(3);
    return '{ const tl = gm.timeline("' + scope + '"); ' +
      'tl.from("' + scope + ' .visual-art", { scale: 0.68, rotate: -11, opacity: 0, duration: 0.82, ease: "back.out(1.45)" }, 0.04)' +
      '.to("' + scope + ' .visual-art", { rotate: 7, scale: 1.035, duration: ' + d + ', ease: "sine.inOut" }, 0.82)' +
      '.from("' + scope + ' .kicker", { y: 24, opacity: 0, duration: 0.48, ease: "expo.out" }, 0.16)' +
      '.from("' + scope + ' .headline .gm-word", { yPercent: 115, rotate: 3, opacity: 0, filter: "blur(12px)", stagger: { each: 0.055, from: "start" }, duration: 0.68, ease: "expo.out" }, 0.28)' +
      '.from("' + scope + ' .subtitle .gm-word", { y: 42, opacity: 0, filter: "blur(7px)", stagger: 0.035, duration: 0.52, ease: "power3.out" }, 0.9)' +
      '.from("' + scope + ' .accent-line", { scaleX: 0, duration: 0.72, ease: "expo.out" }, 0.72)' +
      '.from("' + scope + ' .scene-index", { opacity: 0, y: 12, duration: 0.45, ease: "sine.out" }, 1.15); }';
  }).join("\n");
  const css = [
    '*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden}',
    'body{background:',theme.bg,';color:#fff;font-family:Inter,Arial,sans-serif}',
    '.scene{position:relative;container-type:size;width:100%;height:100%;overflow:hidden;display:grid;place-items:center;background:radial-gradient(ellipse at 70% 18%,',theme.panel,',transparent 52%),linear-gradient(145deg,',theme.bg,',#070910)}',
    '.frame{position:relative;z-index:3;width:90%;height:90%;min-width:0;min-height:0;display:grid;grid-template-rows:46% 50%;grid-template-columns:minmax(0,1fr);gap:4%;overflow:hidden}',
    '.layout-horizontal .frame{grid-template-columns:46% 50%;grid-template-rows:minmax(0,1fr);gap:4%;align-items:center}',
    '.visual{position:relative;min-width:0;min-height:0;width:100%;height:100%;display:grid;place-items:center;overflow:visible}.visual svg{width:100%;height:100%;overflow:visible}.visual-art{transform-box:fill-box;transform-origin:center}',
    '.visual-label{position:absolute;left:2%;bottom:2%;font-size:clamp(9px,1.05cqi,15px);letter-spacing:.18em;font-weight:800;color:#ffffff85}',
    '.copy{width:100%;max-width:100%;max-height:100%;min-width:0;min-height:0;overflow:hidden;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;padding:2% 1%}',
    '.kicker{max-width:100%;font-size:clamp(11px,1.8cqi,24px);line-height:1.2;letter-spacing:.18em;text-transform:uppercase;color:',theme.secondary,';font-weight:800;margin:0 0 2.4cqh;overflow-wrap:anywhere}',
    '.headline{width:100%;max-width:100%;max-height:4.1em;font-family:',FONT[data.style],';font-size:clamp(40px,min(9cqi,10cqh),142px);line-height:1.02;letter-spacing:-.035em;font-weight:850;margin:0;overflow:hidden;overflow-wrap:anywhere;text-wrap:balance}',
    '.gm-word{display:inline-block;margin-right:.12em}',
    '.subtitle{width:100%;max-width:100%;max-height:4.2em;font-size:clamp(15px,min(2.8cqi,3.4cqh),40px);line-height:1.24;color:#e7eaf2;margin:2.5cqh 0 0;overflow:hidden;overflow-wrap:anywhere;text-wrap:balance}',
    '.accent-line{width:clamp(54px,12cqi,180px);height:clamp(4px,.65cqh,9px);flex:none;border-radius:12px;background:linear-gradient(90deg,',theme.accent,',',theme.secondary,');margin-top:3cqh;transform-origin:left}',
    '.scene-index{display:flex;align-items:center;gap:12px;margin-top:2.6cqh;color:#ffffff88;font:700 clamp(10px,1.2cqi,16px)/1 Inter,sans-serif;letter-spacing:.14em}.scene-index i{display:block;width:clamp(26px,5cqi,70px);height:2px;background:',theme.secondary,';opacity:.75}',
    '.layout-horizontal .copy{padding-left:3%}.layout-horizontal .headline{font-size:clamp(48px,min(7.8cqi,10.5cqh),164px)}',
    '.layout-vertical .copy,.layout-square .copy{align-items:center;text-align:center}.layout-vertical .headline,.layout-square .headline,.layout-vertical .subtitle,.layout-square .subtitle{text-align:center}.layout-vertical .accent-line,.layout-square .accent-line{transform-origin:center}.layout-vertical .scene-index,.layout-square .scene-index{justify-content:center}',
    '.glow{position:absolute;width:58%;aspect-ratio:1;border-radius:50%;filter:blur(8cqi);opacity:.22;pointer-events:none;animation:ambient 8s ease-in-out infinite alternate}.glow-a{background:',theme.accent,';right:-18%;top:-25%}.glow-b{background:',theme.secondary,';left:-28%;bottom:-32%;animation-direction:alternate-reverse}',
    '@keyframes ambient{from{transform:translate3d(-3%,-2%,0) scale(.9)}to{transform:translate3d(5%,5%,0) scale(1.12)}}',
    '.scene-grid{position:absolute;inset:-10%;opacity:.12;background-image:linear-gradient(#ffffff18 1px,transparent 1px),linear-gradient(90deg,#ffffff18 1px,transparent 1px);background-size:7cqi 7cqi;transform:perspective(900px) rotateX(58deg) scale(1.4);transform-origin:center bottom;mask-image:linear-gradient(to bottom,transparent,black 30%,transparent 92%)}'
  ].join("");
  return '<!doctype html><html lang="fr" data-width="' + width + '" data-height="' + height + '" data-fps="30" data-duration="' + data.duration + '" data-background="' + theme.bg + '" data-aspect="' + data.aspect + '"><head><meta charset="utf-8"><style>' + css + '</style></head><body><main data-sequence data-transition="push-left ' + transition + '">' + scenes + '</main><script>' + choreography + '</script></body></html>';
}
