/* Driftwatch SPA: hash router + API client + views. No dependencies, no build step. */

import { CLASSES, badge, confidenceDial, hideTooltip, legend, livingWeb, seismograph } from "/assets/viz.js";

async function checkResponse(r) {
  if (!r.ok) {
    let detail = "";
    try { detail = (await r.json()).error ?? ""; } catch { /* non-JSON error body */ }
    throw new Error(detail || `request failed (${r.status})`);
  }
  return r.json();
}

const api = {
  get: (path) => fetch(`/api${path}`).then(checkResponse),
  post: (path, body) => fetch(`/api${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  }).then(checkResponse),
};

const view = document.getElementById("view");
let pollTimer = null;
let lastAlertId = null;

/* ---- utilities ---------------------------------------------------------- */

const html = (strings, ...values) => strings.map((s, i) => s + (values[i] ?? "")).join("");

function esc(value) {
  return String(value ?? "").replace(/[&<>"]/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function fmtValue(value) {
  if (value === null || value === undefined) return "∅";
  if (typeof value === "object") return esc(JSON.stringify(value));
  return esc(String(value));
}

function timeAgo(iso) {
  const seconds = (Date.now() - Date.parse(iso)) / 1000;
  if (!Number.isFinite(seconds)) return "";
  if (seconds < 90) return "just now";
  if (seconds < 5400) return `${Math.round(seconds / 60)}m ago`;
  if (seconds < 129600) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86400)}d ago`;
}

function money(delta) {
  if (delta === null || delta === undefined) return null;
  const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
  return `${sign}$${Math.abs(delta).toLocaleString(undefined, { maximumFractionDigits: 0 })}/mo`;
}

function tile(value, label, note = "", opts = {}) {
  const cls = `tile${opts.hero ? " hero" : ""}${opts.sentiment === "up" ? " up" : opts.sentiment === "down" ? " down" : ""}`;
  const isNumeric = typeof value === "number" && Number.isFinite(value);
  return html`<div class="card ${cls}">
    <div class="tile-value num"${isNumeric ? ` data-count-to="${value}"` : ""}>${esc(isNumeric ? 0 : value)}</div>
    <div class="tile-label">${esc(label)}</div>${note ? `<div class="tile-note">${esc(note)}</div>` : ""}</div>`;
}

function animateCounts(root) {
  for (const node of root.querySelectorAll("[data-count-to]")) {
    const target = Number(node.dataset.countTo);
    node.removeAttribute("data-count-to");
    const start = performance.now();
    const duration = 650;
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      node.textContent = Math.round(target * (1 - Math.pow(1 - t, 3))).toLocaleString();
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
}

function emptyState(title, sub) {
  return fromHtml(html`<div class="empty-state">
    <svg width="52" height="52" viewBox="0 0 52 52" aria-hidden="true">
      <circle cx="26" cy="26" r="20" fill="none" stroke="var(--baseline)" stroke-width="1.5" stroke-dasharray="3 5"/>
      <circle cx="26" cy="26" r="4" fill="var(--baseline)"/></svg>
    <div class="empty-title">${esc(title)}</div>
    <div class="empty-sub">${esc(sub)}</div>
  </div>`);
}

function mount(node, ...children) {
  node.replaceChildren(...children);
  animateCounts(node);
}

function section(titleText) {
  const h = document.createElement("h2");
  h.textContent = titleText;
  return h;
}

function fromHtml(markup) {
  const template = document.createElement("template");
  template.innerHTML = markup.trim();
  return template.content;
}

/* ---- theming --------------------------------------------------------------
   data-theme on <html> drives every color via CSS custom properties (styles.css).
   This layer only ever persists the choice and swaps the favicon — no theme ever
   changes behavior, decisions, or data, only presentation. */

const FAVICONS = {
  dark: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='34' fill='none' stroke='%233987e5' stroke-width='8'/><circle cx='50' cy='50' r='10' fill='%23d03b3b'/></svg>",
  light: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='34' fill='none' stroke='%231f5fc4' stroke-width='8'/><circle cx='50' cy='50' r='10' fill='%23d03b3b'/></svg>",
  spider: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='40' fill='%230a0a14'/><ellipse cx='50' cy='58' rx='14' ry='18' fill='%23f23f55'/><circle cx='50' cy='34' r='9' fill='%23f23f55'/><path d='M38 44 L12 32 M38 52 L8 54 M38 62 L12 74 M62 44 L88 32 M62 52 L92 54 M62 62 L88 74' stroke='%23111' stroke-width='4' fill='none'/></svg>",
};

function applyTheme(theme) {
  const name = FAVICONS[theme] ? theme : "dark";
  document.documentElement.dataset.theme = name;
  document.getElementById("favicon").setAttribute("href", FAVICONS[name]);
  document.querySelectorAll(".theme-switch button").forEach((b) =>
    b.classList.toggle("active", b.dataset.themeSet === name));
  try { localStorage.setItem("dw-theme", name); } catch { /* private browsing, etc. — theme just won't persist */ }
}

document.querySelectorAll(".theme-switch button").forEach((btn) =>
  btn.addEventListener("click", () => applyTheme(btn.dataset.themeSet)));

(() => {
  let saved = "spider";
  try { saved = localStorage.getItem("dw-theme") || "spider"; } catch { /* ignore */ }
  applyTheme(saved);
})();

/* ---- toasts (in-app alert channel) -------------------------------------- */

async function pollAlerts() {
  try {
    const alerts = await api.get("/alerts");
    if (!alerts.length) return;
    if (lastAlertId === null) { lastAlertId = alerts[0].id; return; }
    const fresh = alerts.filter((a) => a.id > lastAlertId).reverse();
    lastAlertId = Math.max(lastAlertId, ...alerts.map((a) => a.id));
    for (const alert of fresh) showToast(alert);
  } catch { /* engine restarting — ignore */ }
}

function showToast(alert) {
  const box = document.getElementById("toasts");
  const node = document.createElement("div");
  node.className = "toast";
  const cls = alert.payload?.class ?? 0;
  node.style.borderLeftColor = CLASSES[cls]?.color ?? "var(--accent)";
  node.append(fromHtml(html`
    <div class="t-head">Driftwatch alert</div>
    <div>${esc(alert.payload?.text ?? "")}</div>
    <time>${esc(new Date(alert.delivered_at).toLocaleTimeString())} · in-app${
      alert.channel === "slack" ? " + slack" : ""}</time>`));
  node.addEventListener("click", () => node.remove());
  box.append(node);
  setTimeout(() => node.remove(), 9500);
}

function showError(message) {
  const box = document.getElementById("toasts");
  const node = document.createElement("div");
  node.className = "toast toast-error";
  node.append(fromHtml(html`
    <div class="t-head">Driftwatch error</div>
    <div>${esc(message)}</div>`));
  node.addEventListener("click", () => node.remove());
  box.append(node);
  setTimeout(() => node.remove(), 9500);
}

/* ---- views --------------------------------------------------------------- */

async function renderWeb() {
  const [sources, stats, events] = await Promise.all([
    api.get("/sources"), api.get("/stats"), api.get("/events?limit=8")]);
  const wrap = document.createElement("div");
  wrap.append(fromHtml(html`
    <h1>The Living Web</h1>
    <p class="sub">Every strand is a public page your stack depends on. Calm means the truth is holding.</p>
    <div class="grid cols-4">
      ${tile(stats.sources, "sources watched")}
      ${tile(Object.entries(stats.events_by_class).reduce((n, [, v]) => n + v, 0), "drift events (12d)")}
      ${tile(stats.heal_mttr_seconds ? `${stats.heal_mttr_seconds}s` : "—", "heal MTTR",
             stats.heal_mttr_seconds ? "detect → verified repair" : "no measured heal yet", { hero: true })}
      ${tile(`${Math.round((stats.heal_verification_pass_rate ?? 0) * 100)}%`, "repairs verified",
             `${stats.credits_spent} Bright Data credits spent`,
             { sentiment: (stats.heal_verification_pass_rate ?? 1) >= 0.9 ? "up" : "down" })}
    </div>`));

  const webCard = document.createElement("div");
  webCard.className = "card";
  webCard.append(sources.length
    ? livingWeb(sources, { onSelect: (id) => { location.hash = `#/sources/${id}`; } })
    : emptyState("No sources watched yet", "Onboard a page from the Sources view to start monitoring."));
  const feed = document.createElement("div");
  feed.className = "card";
  feed.append(fromHtml(`<h2 style="margin-top:0">Latest activity</h2>`));
  const feedList = document.createElement("div");
  feedList.className = "feed";
  if (!events.length) {
    feedList.append(emptyState("All quiet", "No drift events recorded yet — the ledger fills in as runs happen."));
  }
  for (const event of events) {
    const item = document.createElement("a");
    item.className = "feed-item";
    item.href = `#/events/${event.id}`;
    item.style.color = "inherit";
    item.style.borderLeftColor = CLASSES[event.drift_class]?.color ?? "transparent";
    item.append(badge(event.drift_class, { severity: event.severity }));
    item.append(fromHtml(html`<div>${esc(event.summary.slice(0, 130))}</div>
      <time>${esc(event.source_id)} · ${esc(timeAgo(event.created_at))}</time>`));
    feedList.append(item);
  }
  feed.append(feedList);
  const grid = document.createElement("div");
  grid.className = "web-wrap";
  grid.append(webCard, feed);
  wrap.append(grid);
  mount(view, wrap);
}

async function renderSources() {
  const sources = await api.get("/sources");
  const wrap = document.createElement("div");
  wrap.append(fromHtml(html`<h1>Sources</h1>
    <p class="sub">Each source = one Scraper Studio scraper + one semantic contract + one change ledger.</p>`));
  const grid = document.createElement("div");
  grid.className = "grid cols-2";
  for (const source of sources) {
    const card = document.createElement("div");
    card.className = "card";
    card.append(fromHtml(html`
      <h2 class="card-title" style="margin:0 0 2px"><a href="#/sources/${esc(source.id)}">${esc(source.name)}</a></h2>
      <div class="mono" style="color:var(--muted); margin-bottom:10px">${esc(source.url)}</div>
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap">
        <span class="badge">scraper ${esc(source.scraper?.collector_id ?? "—")}</span>
        <span class="badge">template v${esc(source.scraper?.active_version ?? 1)}</span>
        <span class="badge">last run: ${esc(source.last_run?.state ?? "never")}</span>
      </div>`));
    if (source.last_event) {
      const last = document.createElement("div");
      last.style.marginTop = "10px";
      last.append(badge(source.last_event.drift_class));
      last.append(fromHtml(html` <span style="color:var(--muted); font-size:12px">${
        esc(timeAgo(source.last_event.created_at))}</span>`));
      card.append(last);
    }
    grid.append(card);
  }
  wrap.append(grid);
  mount(view, wrap);
}

async function renderSourceDetail(sourceId) {
  const [source, timeline] = await Promise.all([
    api.get(`/sources/${sourceId}`), api.get(`/sources/${sourceId}/timeline`)]);
  const wrap = document.createElement("div");
  wrap.append(fromHtml(html`
    <h1>${esc(source.name)}</h1>
    <p class="sub mono">${esc(source.url)} · collector <a href="${esc(source.scraper?.view_url ?? "#")}"
      target="_blank" rel="noreferrer">${esc(source.scraper?.collector_id ?? "")}</a>
      · template v${esc(source.scraper?.active_version ?? 1)} · every ${esc(source.schedule_minutes)}m</p>`));

  const seismoCard = document.createElement("div");
  seismoCard.className = "card";
  seismoCard.append(section("Seismograph — 13 days"));
  seismoCard.firstChild.style.marginTop = "0";
  seismoCard.append(seismograph(timeline, { onSelectEvent: (id) => { location.hash = `#/events/${id}`; } }));
  seismoCard.append(legend());
  wrap.append(seismoCard);

  if (source.latest_snapshot) {
    const payload = source.latest_snapshot.payload;
    const listKey = payload.models ? "models" : payload.endpoints ? "endpoints" : null;
    if (listKey) {
      const card = document.createElement("div");
      card.className = "card";
      card.style.marginTop = "14px";
      const columns = Object.keys(payload[listKey][0] ?? {});
      card.append(fromHtml(html`
        <h2 style="margin-top:0">Latest verified snapshot
          <span class="sev" style="margin-left:8px">contract-stamped · ${
            esc(timeAgo(source.latest_snapshot.created_at))}</span></h2>
        <div style="overflow:auto"><table>
          <thead><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
          <tbody>${payload[listKey].map((row) => `<tr>${columns.map((c) =>
            `<td class="${typeof row[c] === "number" ? "num" : ""}">${fmtValue(row[c])}</td>`).join("")}
          </tr>`).join("")}</tbody></table></div>`));
      wrap.append(card);
    }
  }

  const contract = source.contract?.spec;
  if (contract) {
    const card = document.createElement("div");
    card.className = "card";
    card.style.marginTop = "14px";
    card.append(fromHtml(html`
      <h2 style="margin-top:0">Semantic contract · v${esc(source.contract.version)}</h2>
      <div class="grid cols-4">
        ${tile(Object.keys(contract.schema?.properties ?? {}).length, "schema properties")}
        ${tile(contract.invariants?.length ?? 0, "invariants")}
        ${tile(contract.assertions?.length ?? 0, "semantic assertions",
               contract.assertions?.[0]?.meaning ?? "")}
        ${tile(contract.continuity?.length ?? 0, "continuity rules")}
      </div>`));
    wrap.append(card);
  }
  mount(view, wrap);
}

async function renderEvents(filterClass = null) {
  const events = await api.get("/events?limit=100");
  const wrap = document.createElement("div");
  wrap.append(fromHtml(html`<h1>Drift events</h1>
    <p class="sub">Every classified change, most recent first. Classes 0–2 never page anyone.</p>`));
  const chips = document.createElement("div");
  chips.className = "chip-row";
  const options = [[null, "All"], [1, "Structural"], [2, "Benign"], [3, "Material"], [4, "Semantic"], [5, "Availability"]];
  for (const [value, label] of options) {
    const chip = document.createElement("button");
    chip.className = `chip${value === filterClass ? " active" : ""}`;
    chip.textContent = label;
    chip.addEventListener("click", () => renderEvents(value));
    chips.append(chip);
  }
  wrap.append(chips);
  const list = document.createElement("div");
  list.className = "grid";
  const filtered = events.filter((e) => filterClass === null || e.drift_class === filterClass);
  if (!filtered.length) {
    list.append(emptyState("No events in this class",
      filterClass === null ? "Nothing has drifted yet." : "Try a different class, or clear the filter."));
  }
  for (const event of filtered) {
    const card = document.createElement("a");
    card.className = "card";
    card.href = `#/events/${event.id}`;
    card.style.color = "inherit";
    card.style.display = "grid";
    card.style.gap = "8px";
    card.style.borderLeftColor = CLASSES[event.drift_class]?.color ?? "transparent";
    const head = document.createElement("div");
    head.style.display = "flex";
    head.style.gap = "10px";
    head.style.alignItems = "center";
    head.append(badge(event.drift_class, { severity: event.severity }));
    head.append(fromHtml(html`<span style="color:var(--muted); font-size:12px">${
      esc(event.source_id)} · ${esc(timeAgo(event.created_at))} · confidence ${esc(event.confidence)}</span>`));
    card.append(head, fromHtml(html`<div>${esc(event.summary)}</div>`));
    list.append(card);
  }
  wrap.append(list);
  mount(view, wrap);
}

function diffTable(changes) {
  const rows = changes.filter((c) => c.path !== "relocation_candidate").map((change) => html`
    <tr><td class="mono">${esc(change.path)}</td>
      <td>${change.kind === "added" ? "—" : `<span class="diff-before">${fmtValue(change.before)}</span>`}</td>
      <td>${change.kind === "removed" ? "—" : `<span class="diff-after">${fmtValue(change.after)}</span>`}</td>
      <td class="sev">${esc(change.kind)}</td></tr>`);
  if (!rows.length) return "";
  return html`<div style="overflow:auto"><table>
    <thead><tr><th>field</th><th>before</th><th>after</th><th></th></tr></thead>
    <tbody>${rows.join("")}</tbody></table></div>`;
}

async function renderEventDetail(eventId) {
  const event = await api.get(`/events/${eventId}`);
  const wrap = document.createElement("div");
  const head = document.createElement("div");
  head.style.display = "flex";
  head.style.gap = "12px";
  head.style.alignItems = "center";
  head.append(badge(event.drift_class, { severity: event.severity }));
  head.append(fromHtml(html`<span style="color:var(--muted)">${esc(event.source_id)} · ${
    esc(new Date(event.created_at).toLocaleString())}</span>`));
  wrap.append(fromHtml(html`<h1>Drift event #${esc(event.id)}</h1>`), head);
  wrap.append(fromHtml(html`<p class="sub" style="margin-top:12px">${esc(event.summary)}</p>`));

  const body = document.createElement("div");
  body.className = "grid cols-2";

  const left = document.createElement("div");
  left.className = "card";
  left.append(fromHtml(`<h2 style="margin-top:0">What changed</h2>`));
  const changes = event.field_changes ?? [];
  if (event.drift_class === 4) {
    const unitChange = changes.find((c) => c.path.includes("unit_context"));
    if (unitChange) {
      const entity = (unitChange.path.match(/\[([^\]]+)\]/) || [])[1] ?? "";
      left.append(fromHtml(html`<div class="semantic-hero">
        ${entity ? `<div class="sh-row"><span class="sev">${esc(entity)}</span></div>` : ""}
        <div class="sh-row">
          <span class="sh-unit-before">${esc(unitChange.before)}</span><span>→</span>
          <span class="sh-unit-after">${esc(unitChange.after)}</span>
        </div>
        <div class="sh-caption">The extracted number didn't move. What it means did — only the semantics gate catches that.</div>
      </div>`));
    }
  }
  left.append(fromHtml(diffTable(changes) || `<p class="sub">No field-level diff (extraction-level event).</p>`));
  const relocations = changes.filter((c) => c.path === "relocation_candidate");
  if (relocations.length) {
    left.append(fromHtml(html`<h2>Relocation candidates (via Bright Data discover)</h2>
      <table><thead><tr><th>candidate</th><th>score</th><th>reason</th></tr></thead><tbody>
      ${relocations.map((r) => html`<tr><td class="mono">${esc(r.after?.url)}</td>
        <td class="num">${esc(r.after?.score)}</td><td>${esc(r.after?.reason)}</td></tr>`).join("")}
      </tbody></table>`));
  }

  const right = document.createElement("div");
  right.style.display = "grid";
  right.style.gap = "14px";
  const dialCard = document.createElement("div");
  dialCard.className = "card";
  dialCard.style.display = "flex";
  dialCard.style.gap = "18px";
  dialCard.style.alignItems = "center";
  dialCard.append(confidenceDial(event.confidence, "confidence"));
  dialCard.append(fromHtml(html`<div style="flex:1; min-width:0">
    <div class="tile-label">verification verdict</div>
    <div class="gates" style="margin-top:4px">${event.after_verdict ? event.after_verdict.gates.map((gate) => {
      const hero = gate.gate === "semantics" && !gate.passed;
      return html`<div class="gate ${gate.passed ? "pass" : "fail"}">
        <div class="gate-dot${hero ? " hero" : ""}">${gate.passed ? "✓" : "✕"}</div>
        <div><div class="gate-name">${esc(gate.gate)}</div>
          <div class="gate-detail">${esc(gate.details?.[0] ?? "").slice(0, 90)}</div></div>
        <div></div></div>`;
    }).join("") : `<span class="sub">n/a</span>`}</div></div>`));
  right.append(dialCard);

  if (event.impact) {
    const impact = document.createElement("div");
    impact.className = "card";
    const cost = money(event.impact.cost_delta_monthly);
    impact.append(fromHtml(html`
      <h2 style="margin-top:0">Blast radius</h2>
      ${cost ? `<div class="tile-value num" style="color:${(event.impact.cost_delta_monthly ?? 0) > 0 ?
        "var(--c3)" : "var(--good)"}">${esc(cost)}</div>
        <div class="tile-label" style="margin-bottom:10px">estimated cost delta (declared usage profile)</div>` : ""}
      ${event.impact.affected?.length ? html`<table>
        <thead><tr><th>file</th><th>line</th><th>call site</th></tr></thead>
        <tbody>${event.impact.affected.slice(0, 10).map((site) => html`
          <tr><td class="mono">${esc(site.file)}</td><td class="num">${esc(site.line)}</td>
          <td class="mono">${esc(site.snippet)}</td></tr>`).join("")}</tbody></table>` :
        `<p class="sub">No call sites matched in the connected repo.</p>`}
      <h2>Migration note</h2>
      <div class="prompt-block">${esc(event.impact.migration_note)}</div>`));
    right.append(impact);
  }

  if (event.heal) {
    const heal = document.createElement("div");
    heal.className = "card";
    heal.append(fromHtml(html`
      <h2 style="margin-top:0">Self-heal record
        <span class="sev" style="margin-left:8px">${esc(event.heal.decision ?? event.heal.status)}${
          event.heal.mttr_seconds ? ` · MTTR ${esc(event.heal.mttr_seconds)}s` : ""}</span></h2>
      <div class="tile-label" style="margin-bottom:6px">machine-composed heal prompt (sent to Scraper Studio)</div>
      <div class="prompt-block">${esc(event.heal.composed_prompt)}</div>`));
    right.append(heal);
  }

  if (event.alerts?.length) {
    const alerts = document.createElement("div");
    alerts.className = "card";
    alerts.append(fromHtml(html`<h2 style="margin-top:0">Alerts delivered</h2>${
      event.alerts.map((a) => html`<div class="feed-item" style="margin-top:8px">
        <div>${esc(a.payload?.text ?? "")}</div>
        <time>${esc(a.channel)} · ${esc(new Date(a.delivered_at).toLocaleString())}</time></div>`).join("")}`));
    right.append(alerts);
  }

  body.append(left, right);
  wrap.append(body);
  mount(view, wrap);
}

const GATE_STEPS = [
  ["detect", "Contract validation caught the failure"],
  ["diagnose", "Failing fields + last-known-good examples identified"],
  ["heal", "Machine-composed prompt sent to Bright Data scraper heal"],
  ["verify", "preview_result re-proven against the full contract"],
  ["approve", "scraper approve driven by the three-band policy"],
];

async function renderHeal() {
  const [heals, reviewQueue, stats] = await Promise.all([
    api.get("/heals"), api.get("/review"), api.get("/stats")]);
  const wrap = document.createElement("div");
  wrap.append(fromHtml(html`<h1>Heal Center</h1>
    <p class="sub">A healed scraper's output is never trusted — it is re-proven against the contract.</p>
    <div class="grid cols-4">
      ${tile(stats.heal_mttr_seconds ? `${stats.heal_mttr_seconds}s` : "—", "mean time to verified repair",
             stats.heal_mttr_seconds ? "" : "no measured heal yet — seeded demo history is excluded", { hero: true })}
      ${tile(`${Math.round((stats.heal_verification_pass_rate ?? 0) * 100)}%`, "repairs verified & approved", "",
             { sentiment: (stats.heal_verification_pass_rate ?? 1) >= 0.9 ? "up" : "down" })}
      ${tile(stats.quarantined_snapshots, "snapshots quarantined", "never served downstream")}
      ${tile(stats.credits_spent, "Bright Data credits spent", "1 credit per page load")}
    </div>`));

  const latest = heals[0];
  const gatesCard = document.createElement("div");
  gatesCard.className = "card";
  gatesCard.style.marginTop = "14px";
  gatesCard.append(fromHtml(html`<h2 style="margin-top:0">Autonomous repair sequence${
    latest ? ` — latest: ${esc(latest.source_id)} (${esc(timeAgo(latest.created_at))})` : ""}</h2>`));
  const gates = document.createElement("div");
  gates.className = "gates";
  const verdictGates = latest?.verification?.gates ?? [];
  const gateState = (step) => {
    if (!latest) return "";
    if (step === "verify") return verdictGates.every((g) => g.passed) ? "pass" : "fail";
    if (step === "approve") return latest.status === "approved" ? "pass" :
      latest.status === "review" ? "run" : "fail";
    return "pass";
  };
  for (const [step, description] of GATE_STEPS) {
    const state = gateState(step);
    gates.append(fromHtml(html`<div class="gate ${state}">
      <div class="gate-dot">${state === "pass" ? "✓" : state === "fail" ? "✕" : state === "run" ? "…" : "•"}</div>
      <div><div class="gate-name">${esc(step)}</div><div class="gate-detail">${esc(description)}</div></div>
      <div class="sev">${step === "verify" && latest ?
        `${verdictGates.filter((g) => g.passed).length}/${verdictGates.length} gates` : ""}</div></div>`));
  }
  gatesCard.append(gates);
  wrap.append(gatesCard);

  wrap.append(section(`Review queue (${reviewQueue.length})`));
  if (!reviewQueue.length) {
    wrap.append(fromHtml(`<p class="sub">Empty — every recent repair cleared the auto-approve band.</p>`));
  }
  for (const heal of reviewQueue) {
    const card = document.createElement("div");
    card.className = "card";
    card.style.marginBottom = "12px";
    card.append(fromHtml(html`
      <h2 style="margin-top:0">${esc(heal.source_id)} · confidence in gray band</h2>
      <div class="tile-label" style="margin:2px 0 6px">machine-composed prompt</div>
      <div class="prompt-block">${esc(heal.composed_prompt)}</div>
      <div class="tile-label" style="margin:10px 0 6px">verification of Bright Data's preview</div>
      <div>${(heal.verification?.gates ?? []).map((gate) => html`
        <span class="badge" style="margin:0 6px 6px 0; color:${gate.passed ? "var(--good)" : "var(--c3)"}">
        ${gate.passed ? "✓" : "✕"} ${esc(gate.gate)}</span>`).join("")}</div>`));
    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "10px";
    actions.style.marginTop = "12px";
    const approve = document.createElement("button");
    approve.className = "btn";
    approve.textContent = "Approve repair";
    approve.addEventListener("click", async () => {
      approve.disabled = true;
      try {
        await api.post(`/review/${heal.id}`, { approve: true });
        renderHeal();
      } catch (err) {
        showError(`Approve failed: ${err.message}`);
        approve.disabled = false;
      }
    });
    const reject = document.createElement("button");
    reject.className = "btn btn-danger";
    reject.textContent = "Reject";
    reject.addEventListener("click", async () => {
      reject.disabled = true;
      try {
        await api.post(`/review/${heal.id}`, { approve: false });
        renderHeal();
      } catch (err) {
        showError(`Reject failed: ${err.message}`);
        reject.disabled = false;
      }
    });
    actions.append(approve, reject);
    card.append(actions);
    wrap.append(card);
  }

  wrap.append(section("Heal history"));
  if (!heals.length) {
    const box = document.createElement("div");
    box.className = "card";
    box.append(emptyState("No heals yet", "This source hasn't needed a repair — a green history is a quiet one."));
    wrap.append(box);
    mount(view, wrap);
    return;
  }
  const table = fromHtml(html`<div class="card" style="overflow:auto"><table>
    <thead><tr><th>when</th><th>source</th><th>decision</th><th>by</th><th>version</th><th>MTTR</th></tr></thead>
    <tbody>${heals.map((heal) => html`<tr>
      <td>${esc(timeAgo(heal.created_at))}</td>
      <td>${esc(heal.source_id)}</td>
      <td>${esc(heal.decision ?? heal.status)}</td>
      <td>${esc(heal.decided_by ?? "—")}</td>
      <td class="num">${heal.version_after ? `v${esc(heal.version_before)}→v${esc(heal.version_after)}` :
        `v${esc(heal.version_before)} kept`}</td>
      <td class="num">${heal.mttr_seconds ? `${esc(heal.mttr_seconds)}s${heal.seeded ? " (seeded)" : ""}` : "—"}</td></tr>`).join("")}
    </tbody></table></div>`);
  wrap.append(table);
  mount(view, wrap);
}

async function renderLedger() {
  const entries = await api.get("/ledger?limit=200");
  const wrap = document.createElement("div");
  wrap.append(fromHtml(html`<h1>Audit ledger</h1>
    <p class="sub">Append-only. Every run, verdict, heal prompt, approval and alert — machine and human alike.</p>
    <div class="card" style="overflow:auto"><table>
      <thead><tr><th>when</th><th>actor</th><th>action</th><th>refs</th><th>payload</th></tr></thead>
      <tbody>${entries.map((entry) => html`<tr>
        <td style="white-space:nowrap">${esc(new Date(entry.created_at).toLocaleString())}</td>
        <td><span class="badge">${esc(entry.actor)}</span></td>
        <td class="mono">${esc(entry.action)}</td>
        <td class="mono">${esc(JSON.stringify(entry.refs))}</td>
        <td>${Object.keys(entry.payload ?? {}).length ? html`<details><summary class="sev">view</summary>
          <div class="prompt-block" style="margin-top:6px">${esc(JSON.stringify(entry.payload, null, 2))}</div>
          </details>` : ""}</td></tr>`).join("")}
      </tbody></table></div>`));
  mount(view, wrap);
}

/* ---- demo drawer --------------------------------------------------------- */

const VARIANTS = [
  ["v1_baseline", "v1 — baseline page"],
  ["v2_redesign", "v2 — overnight redesign (breaks template)"],
  ["v3_semantic", "v3 — unit meaning silently changes"],
  ["v4_material", "v4 — real price/param change"],
  ["v5_gone", "v5 — page removed (404)"],
];

async function buildDrawer() {
  const drawer = document.getElementById("demo-drawer");
  const [sources, state] = await Promise.all([api.get("/sources"), api.get("/demo/state")]);
  drawer.replaceChildren(fromHtml(html`
    <h3>Demo controls</h3>
    <p class="sub">Set what each mirrored page looks like, then run the pipeline against it.
      Same engine, simulated web.</p>
    ${sources.map((source) => html`
      <div class="demo-row">
        <label>${esc(source.name)} <a href="/mirror/${esc(source.id)}" target="_blank"
          rel="noreferrer" style="font-weight:400">view page ↗</a></label>
        <select data-source="${esc(source.id)}">
          ${VARIANTS.map(([value, label]) => html`<option value="${value}" ${
            state[source.id] === value ? "selected" : ""}>${label}</option>`).join("")}
        </select>
      </div>`).join("")}
    <div style="display:flex; gap:10px">
      <button class="btn" id="demo-apply">Apply & run all</button>
      <button class="ghost-btn" id="demo-close">Close</button>
    </div>`));
  drawer.querySelector("#demo-apply").addEventListener("click", async (click) => {
    click.target.disabled = true;
    try {
      for (const select of drawer.querySelectorAll("select[data-source]")) {
        await api.post("/demo/state", { source_id: select.dataset.source, variant: select.value });
      }
      await api.post("/run-all");
      route();
    } catch (err) {
      showError(`Demo update failed: ${err.message}`);
    } finally {
      click.target.disabled = false;
    }
  });
  drawer.querySelector("#demo-close").addEventListener("click", () => { drawer.hidden = true; });
}

/* ---- router --------------------------------------------------------------- */

const routes = [
  [/^#\/web$/, () => renderWeb(), "web", true],
  [/^#\/sources$/, () => renderSources(), "sources", true],
  [/^#\/sources\/([\w-]+)$/, (m) => renderSourceDetail(m[1]), "sources", false],
  [/^#\/events$/, () => renderEvents(), "events", true],
  [/^#\/events\/(\d+)$/, (m) => renderEventDetail(m[1]), "events", false],
  [/^#\/heal$/, () => renderHeal(), "heal", true],
  [/^#\/ledger$/, () => renderLedger(), "ledger", false],
];

async function route() {
  const hash = location.hash || "#/web";
  hideTooltip();
  clearInterval(pollTimer);
  for (const [pattern, render, nav, poll] of routes) {
    const match = hash.match(pattern);
    if (!match) continue;
    document.querySelectorAll(".rail a[data-nav]").forEach((a) =>
      a.classList.toggle("active", a.dataset.nav === nav));
    view.classList.add("loading");
    try {
      await render(match);
    } catch (err) {
      showError(`Couldn't load this view: ${err.message}`);
      mount(view, emptyState("Something went wrong", "The engine may be waking up or unreachable — try again in a moment."));
    } finally {
      view.classList.remove("loading");
    }
    if (poll) pollTimer = setInterval(() => render(match).catch((err) => showError(`Refresh failed: ${err.message}`)), 4000);
    return;
  }
  location.hash = "#/web";
}

window.addEventListener("hashchange", route);
document.getElementById("demo-toggle").addEventListener("click", async () => {
  const drawer = document.getElementById("demo-drawer");
  if (drawer.hidden) await buildDrawer();
  drawer.hidden = !drawer.hidden;
});

route();
setInterval(pollAlerts, 3000);
pollAlerts();
