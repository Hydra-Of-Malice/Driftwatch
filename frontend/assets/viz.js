/* SVG visualization builders (no dependencies).
   Every class mark = color + glyph + label: identity never rides on color alone. */

export const CLASSES = {
  0: { key: "none", label: "No change", color: "var(--muted)", glyph: "dot" },
  1: { key: "structural", label: "Structural", color: "var(--c1)", glyph: "triangle" },
  2: { key: "benign", label: "Benign", color: "var(--c2)", glyph: "dot" },
  3: { key: "material", label: "Material", color: "var(--c3)", glyph: "square" },
  4: { key: "semantic", label: "Semantic", color: "var(--c4)", glyph: "diamond" },
  5: { key: "availability", label: "Availability", color: "var(--c5)", glyph: "ring" },
};

const SVG_NS = "http://www.w3.org/2000/svg";

export function el(tag, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  for (const child of children) node.append(child);
  return node;
}

/** Class glyph as an SVG group centered on (0,0); size ~= r*2. */
export function glyph(kind, r, color, strokeW = 1.75) {
  const common = { fill: "none", stroke: color, "stroke-width": strokeW, "stroke-linejoin": "round" };
  if (kind === "triangle") {
    return el("path", { ...common, d: `M 0 ${-r} L ${r * 0.9} ${r * 0.75} L ${-r * 0.9} ${r * 0.75} Z` });
  }
  if (kind === "square") {
    const s = r * 0.85;
    return el("rect", { ...common, x: -s, y: -s, width: s * 2, height: s * 2, rx: 1.5 });
  }
  if (kind === "diamond") {
    return el("path", { ...common, d: `M 0 ${-r} L ${r} 0 L 0 ${r} L ${-r} 0 Z` });
  }
  if (kind === "ring") {
    return el("circle", { ...common, r: r * 0.8 });
  }
  return el("circle", { fill: color, r: Math.max(2.5, r * 0.5) }); // dot
}

export function badge(driftClass, { severity } = {}) {
  const meta = CLASSES[driftClass] ?? CLASSES[0];
  const wrap = document.createElement("span");
  wrap.className = "badge";
  const svg = el("svg", { class: "glyph", width: 14, height: 14, viewBox: "-7 -7 14 14" });
  svg.append(glyph(meta.glyph, 5, meta.color));
  wrap.append(svg, document.createTextNode(driftClass === 0 ? meta.label : `Class ${driftClass} · ${meta.label}`));
  if (severity) {
    const sev = document.createElement("span");
    sev.className = "sev";
    sev.textContent = severity;
    wrap.append(sev);
  }
  return wrap;
}

export function legend(classIds = [1, 2, 3, 4, 5]) {
  const box = document.createElement("div");
  box.className = "legend";
  for (const id of classIds) {
    const meta = CLASSES[id];
    const item = document.createElement("span");
    const svg = el("svg", { width: 14, height: 14, viewBox: "-7 -7 14 14" });
    svg.append(glyph(meta.glyph, 5, meta.color));
    item.append(svg, document.createTextNode(meta.label));
    box.append(item);
  }
  return box;
}

/* ---- tooltip ------------------------------------------------------------ */

const tooltipEl = () => document.getElementById("tooltip");

export function showTooltip(html, x, y) {
  const tip = tooltipEl();
  tip.innerHTML = html;
  tip.hidden = false;
  const pad = 14;
  const rect = tip.getBoundingClientRect();
  tip.style.left = `${Math.min(x + pad, window.innerWidth - rect.width - pad)}px`;
  tip.style.top = `${Math.min(y + pad, window.innerHeight - rect.height - pad)}px`;
}

export function hideTooltip() {
  tooltipEl().hidden = true;
}

/* ---- the Living Web ----------------------------------------------------- */

export function livingWeb(sources, { onSelect } = {}) {
  const W = 640;
  const H = 480;
  const cx = W / 2;
  const cy = H / 2 + 6;
  const R = 168;
  const svg = el("svg", { class: "web-svg", viewBox: `0 0 ${W} ${H}`, role: "img",
                          "aria-label": "Living Web: monitored dependencies" });

  // ambient concentric rings
  for (const r of [R * 0.45, R * 0.75, R * 1.05]) {
    svg.append(el("circle", { cx, cy, r, fill: "none", stroke: "var(--grid)", "stroke-width": 1,
                              "stroke-dasharray": "2 5" }));
  }

  const n = Math.max(sources.length, 1);
  sources.forEach((source, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2 + (n === 2 ? Math.PI / 4 : 0);
    const x = cx + Math.cos(angle) * R;
    const y = cy + Math.sin(angle) * R;
    const cls = source.last_event ? source.last_event.drift_class : 0;
    const meta = CLASSES[cls] ?? CLASSES[0];
    const recent = source.last_event &&
      Date.now() - Date.parse(source.last_event.created_at) < 36e5; // within the hour

    const group = el("g", { class: recent ? "strand-group tremor" : "strand-group", cursor: "pointer" });
    group.append(el("line", { class: recent ? "strand tremor" : "strand", x1: cx, y1: cy, x2: x, y2: y }));

    // a faint pulse traveling the strand — the visual claim that this is watched continuously, not a static diagram
    const particle = el("circle", { class: "strand-particle", r: 2.2 });
    particle.append(el("animateMotion", {
      dur: `${2.6 + i * 0.5}s`, repeatCount: "indefinite", path: `M ${cx} ${cy} L ${x} ${y}`,
    }));
    particle.append(el("animate", {
      attributeName: "opacity", values: "0;0.85;0", keyTimes: "0;0.5;1",
      dur: `${2.6 + i * 0.5}s`, repeatCount: "indefinite",
    }));
    group.append(particle);

    if (recent) {
      const ripple = el("circle", { class: "ripple go", cx: x, cy: y, r: 26, stroke: meta.color,
                                    "stroke-width": 2 });
      group.append(ripple);
    }
    const quarantined = source.last_run && ["review", "quarantined", "relocating"].includes(source.last_run.state);
    group.append(el("circle", { class: "node-core", cx: x, cy: y, r: 26, "stroke-width": 1.5,
                                stroke: recent || quarantined ? meta.color : "var(--ring)" }));
    const g = el("g", { transform: `translate(${x} ${y})` });
    g.append(glyph(meta.glyph, 8, cls === 0 ? "var(--good)" : meta.color, 2));
    group.append(g);

    const labelY = y + (y >= cy ? 46 : -38);
    const label = el("text", { class: "node-label", x, y: labelY, "text-anchor": "middle" });
    label.textContent = source.name.split(" — ")[0];
    const sub = el("text", { class: "node-sub", x, y: labelY + 14, "text-anchor": "middle" });
    sub.textContent = quarantined ? "needs review" : cls === 0 ? "verified" :
      (CLASSES[cls]?.label ?? "").toLowerCase();
    group.append(label, sub);

    group.addEventListener("click", () => onSelect?.(source.id));
    group.addEventListener("mousemove", (event) => {
      const state = source.last_run?.state ?? "idle";
      showTooltip(
        `<strong>${source.name}</strong><br/><span class="tt-sub">last run: ${state} · ` +
        `v${source.scraper?.active_version ?? 1} · ${source.last_event ? source.last_event.class_label : "no events"}</span>`,
        event.clientX, event.clientY);
    });
    group.addEventListener("mouseleave", hideTooltip);
    svg.append(group);
  });

  // center: the stack — a slow always-on breathing pulse, not conditional on drift
  svg.append(el("circle", { class: "node-core center", cx, cy, r: 34 }));
  const core = el("text", { class: "node-label", x: cx, y: cy + 4, "text-anchor": "middle" });
  core.textContent = "your stack";
  svg.append(core);
  return svg;
}

/* ---- the Seismograph ----------------------------------------------------- */

export function seismograph(timeline, { days = 13, onSelectEvent } = {}) {
  const W = 860;
  const H = 150;
  const padL = 10;
  const padR = 10;
  const baseY = H - 38;
  const now = Date.now();
  const t0 = now - days * 864e5;
  const x = (ts) => padL + ((ts - t0) / (now - t0)) * (W - padL - padR);

  const svg = el("svg", { class: "seismo", viewBox: `0 0 ${W} ${H}`, role: "img",
                          "aria-label": `Drift events, last ${days} days` });

  for (let d = 0; d <= days; d++) {
    const ts = t0 + d * 864e5;
    const gx = x(ts);
    svg.append(el("line", { class: "gridline", x1: gx, y1: 18, x2: gx, y2: baseY }));
    if (d % 2 === 0) {
      const label = el("text", { class: "tick-label", x: gx + 3, y: H - 22 });
      label.textContent = new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
      svg.append(label);
    }
  }
  svg.append(el("line", { class: "base", x1: padL, y1: baseY, x2: W - padR, y2: baseY }));

  // faint run pulse: a tick per run, confidence-scaled
  for (const run of timeline.runs ?? []) {
    const ts = Date.parse(run.started_at);
    if (Number.isNaN(ts) || ts < t0) continue;
    const h = 3 + (run.confidence ?? 0.9) * 5;
    svg.append(el("line", { x1: x(ts), y1: baseY - h, x2: x(ts), y2: baseY,
                            stroke: "var(--baseline)", "stroke-width": 1 }));
  }

  const spikeH = { 1: 44, 2: 16, 3: 62, 4: 62, 5: 52 };
  for (const event of timeline.events ?? []) {
    const ts = Date.parse(event.created_at);
    if (Number.isNaN(ts) || ts < t0) continue;
    const meta = CLASSES[event.drift_class] ?? CLASSES[0];
    const ex = x(ts);
    const h = spikeH[event.drift_class] ?? 20;
    const group = el("g", { cursor: "pointer" });
    group.append(el("line", { x1: ex, y1: baseY - h, x2: ex, y2: baseY, stroke: meta.color,
                              "stroke-width": 2, "stroke-linecap": "round" }));
    const gl = el("g", { transform: `translate(${ex} ${baseY - h - 8})` });
    gl.append(glyph(meta.glyph, 6, meta.color));
    group.append(gl);
    // invisible hit target (bigger than the mark)
    group.append(el("rect", { x: ex - 9, y: baseY - h - 18, width: 18, height: h + 18,
                              fill: "transparent" }));
    group.addEventListener("mousemove", (mouse) => showTooltip(
      `<strong>Class ${event.drift_class} · ${meta.label}</strong><br/>` +
      `${event.summary.slice(0, 140)}<br/><span class="tt-sub">` +
      `${new Date(ts).toLocaleString()} · confidence ${event.confidence}</span>`,
      mouse.clientX, mouse.clientY));
    group.addEventListener("mouseleave", hideTooltip);
    group.addEventListener("click", () => onSelectEvent?.(event.id));
    svg.append(group);
  }

  // version-bump annotations from heals
  for (const heal of timeline.heals ?? []) {
    if (heal.status !== "approved") continue;
    const ts = Date.parse(heal.created_at);
    if (Number.isNaN(ts) || ts < t0) continue;
    const hx = x(ts);
    const label = el("text", { class: "tick-label", x: hx + 4, y: 26, fill: "var(--good)" });
    label.textContent = `v${heal.version_before}→v${heal.version_after} ✓`;
    svg.append(label);
  }
  return svg;
}

/* ---- confidence dial ----------------------------------------------------- */

export function confidenceDial(value, caption = "confidence") {
  const size = 92;
  const r = 36;
  const c = size / 2;
  const circumference = 2 * Math.PI * r;
  const arc = Math.max(0, Math.min(1, value ?? 0)) * circumference * 0.75;
  const svg = el("svg", { width: size, height: size, viewBox: `0 0 ${size} ${size}`, role: "img",
                          "aria-label": `${caption}: ${Math.round((value ?? 0) * 100)}%` });
  const rotate = `rotate(135 ${c} ${c})`;
  svg.append(el("circle", { class: "dial-track", cx: c, cy: c, r, fill: "none", "stroke-width": 7,
                            "stroke-dasharray": `${circumference * 0.75} ${circumference}`, transform: rotate,
                            "stroke-linecap": "round" }));
  svg.append(el("circle", { class: "dial-arc", cx: c, cy: c, r, fill: "none", "stroke-width": 7,
                            "stroke-dasharray": `${arc} ${circumference}`, transform: rotate,
                            "stroke-linecap": "round" }));
  const num = el("text", { class: "dial-num", x: c, y: c + 4, "text-anchor": "middle" });
  num.textContent = value == null ? "—" : `${Math.round(value * 100)}%`;
  const cap = el("text", { class: "dial-cap", x: c, y: c + 20, "text-anchor": "middle" });
  cap.textContent = caption;
  svg.append(num, cap);
  return svg;
}
