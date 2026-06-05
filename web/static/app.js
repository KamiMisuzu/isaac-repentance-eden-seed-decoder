const HISTORY_KEY = "eden_ops_history";
const HISTORY_MAX = 40;

const form = document.getElementById("form");
const reverseForm = document.getElementById("reverseForm");
const predictPanel = document.getElementById("predictPanel");
const reversePanel = document.getElementById("reversePanel");
const reverseWorkspace = document.getElementById("reverseWorkspace");
const seedEl = document.getElementById("seed");
const errEl = document.getElementById("err");
const outEl = document.getElementById("out");
const revPhaseEl = document.getElementById("revPhase");
const revBarFillEl = document.getElementById("revBarFill");
const revStatsEl = document.getElementById("revStats");
const revLogEl = document.getElementById("revLog");
const seedListEl = document.getElementById("seedList");
const resultsMetaEl = document.getElementById("resultsMeta");
const btnReverseStop = document.getElementById("btnReverseStop");
const btn = document.getElementById("btn");
const btnReverse = document.getElementById("btnReverse");
const btnReverseContinue = document.getElementById("btnReverseContinue");
const dataPathEl = document.getElementById("dataPath");
const dataStatusEl = document.getElementById("dataStatus");
const extractMsgEl = document.getElementById("extractMsg");
const btnExtract = document.getElementById("btnExtract");
const modeTabs = document.querySelectorAll(".mode-tab");
const historyListEl = document.getElementById("historyList");
const btnClearHistory = document.getElementById("btnClearHistory");
const pocketFieldsEl = document.getElementById("pocketFields");
const fieldTrinketEl = document.getElementById("fieldTrinket");
const fieldPocketEl = document.getElementById("fieldPocket");

let mode = "predict";
let reverseAbort = null;
const revLogLines = [];
let reverseSession = null;
let lastDisplay = null;
let lastProfileStatus = null;

function u32ToHex(n) {
  return "0x" + (Number(n) >>> 0).toString(16).padStart(8, "0");
}

function setRevStartInput(u32) {
  const el = document.getElementById("rev_start");
  if (!el) return;
  el.value = u32ToHex(Number(u32) >>> 0);
}

function showContinueButton(show) {
  if (!btnReverseContinue) return;
  btnReverseContinue.classList.toggle("hidden", !show);
}

function resetReverseSession() {
  reverseSession = null;
  showContinueButton(false);
}

function setMode(next) {
  mode = next;
  modeTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === next));
  predictPanel.classList.toggle("hidden", next !== "predict");
  reversePanel.classList.toggle("hidden", next !== "reverse");
  errEl.classList.add("hidden");
  outEl.classList.add("hidden");
  renderHistoryList();
}

modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveHistoryEntry(entry) {
  const list = loadHistory();
  list.unshift(entry);
  if (list.length > HISTORY_MAX) list.length = HISTORY_MAX;
  localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
  renderHistoryList();
}

function clearHistory() {
  localStorage.removeItem(HISTORY_KEY);
  renderHistoryList();
}

function formatTime(iso) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function statLabel(key) {
  return t(`stat.${key}`);
}

function roleLabel(role) {
  if (role === "被动" || role === "Passive") return t("role.passive");
  if (role === "主动" || role === "Active") return t("role.active");
  const lower = String(role).toLowerCase();
  if (lower.includes("passive")) return t("role.passive");
  if (lower.includes("active")) return t("role.active");
  return role;
}

function summarizeCriteria(body) {
  const parts = [];
  if (body.seed_prefix) parts.push(t("crit.prefix", { v: body.seed_prefix }));
  if (body.red) parts.push(t("crit.red", { v: body.red }));
  if (body.soul) parts.push(t("crit.soul", { v: body.soul }));
  if (body.passive_id) parts.push(t("crit.passive", { v: body.passive_id }));
  if (body.active_id) parts.push(t("crit.active", { v: body.active_id }));
  if (body.pocket_kind) {
    if (body.pocket_kind === "trinket" && body.trinket_id) {
      parts.push(t("crit.trinket", { v: body.trinket_id }));
    } else if (body.pocket_id) {
      parts.push(t("crit.pocket", { v: body.pocket_id }));
    } else {
      parts.push(t(`pocket.${body.pocket_kind}`));
    }
  }
  return parts.length ? parts.join(" · ") : t("crit.none");
}

function renderHistoryList() {
  const list = loadHistory();
  if (!historyListEl) return;

  if (list.length === 0) {
    historyListEl.innerHTML = `<p class="history-empty">${t("history.empty")}</p>`;
    return;
  }

  historyListEl.innerHTML = list
    .map(
      (h, i) => `
    <div class="history-item" data-idx="${i}">
      <div class="history-row">
        <span class="history-tag">${h.mode === "reverse" ? t("history.reverse") : t("history.predict")}</span>
        <span class="history-time">${formatTime(h.time)}</span>
      </div>
      <div class="history-summary">${h.summary}</div>
    </div>`
    )
    .join("");

  historyListEl.querySelectorAll(".history-item").forEach((el) => {
    el.addEventListener("click", () => {
      const h = list[Number(el.dataset.idx)];
      if (!h) return;
      if (h.mode === "reverse") {
        setMode("reverse");
        applyReverseCriteria(h.criteria || {});
      } else if (h.seed) {
        setMode("predict");
        seedEl.value = h.seed;
        form.requestSubmit();
      }
    });
  });
}

function applyReverseCriteria(c) {
  const set = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.value = v ?? "";
  };
  set("rev_prefix", c.seed_prefix || "");
  set("rev_start", c.start_u32 || "");
  set("rev_end", c.end_u32 || "");
  updateReverseScanMode();
  set("rev_max_results", c.max_results || "50");
  set("rev_max_scan", c.max_scan || "5000000");
  set("rev_workers", c.workers || "4");
  set("rev_red", c.red || "");
  set("rev_soul", c.soul || "");
  set("rev_damage", c.damage || "");
  set("rev_speed", c.speed || "");
  set("rev_tears", c.tears || "");
  set("rev_range", c.range || "");
  set("rev_shotSpeed", c.shotSpeed || "");
  set("rev_luck", c.luck || "");
  set("rev_trinket_id", c.trinket_id || "");
  set("rev_pocket_id", c.pocket_id || "");
  set("rev_passive_id", c.passive_id || "");
  set("rev_active_id", c.active_id || "");
  document.getElementById("rev_ach_159").checked = c.ach_159 === "1";
  const pk = c.pocket_kind || "";
  const radio = document.querySelector(`input[name="pocket_kind"][value="${pk}"]`);
  if (radio) radio.checked = true;
  updatePocketFields();
  resetReverseSession();
}

function updatePocketFields() {
  const pk = document.querySelector('input[name="pocket_kind"]:checked')?.value || "";
  fieldTrinketEl.classList.add("hidden");
  fieldPocketEl.classList.add("hidden");
  pocketFieldsEl.classList.add("hidden");

  if (pk === "trinket") {
    pocketFieldsEl.classList.remove("hidden");
    fieldTrinketEl.classList.remove("hidden");
  } else if (pk === "card" || pk === "pill") {
    pocketFieldsEl.classList.remove("hidden");
    fieldPocketEl.classList.remove("hidden");
    const helpKey = `pocket.${pk}Id`;
    const lbl = fieldPocketEl.querySelector(".pf-lbl");
    if (lbl) {
      lbl.dataset.i18n = helpKey;
      lbl.textContent = t(helpKey);
    }
    const btn = fieldPocketEl.querySelector(".pf-help");
    const pop = fieldPocketEl.querySelector(".pf-pop");
    const note = fieldPocketEl.querySelector(".pf-note");
    const code = fieldPocketEl.querySelector(".pf-code");
    if (btn) btn.dataset.help = helpKey;
    if (pop) pop.dataset.helpPop = helpKey;
    if (note) {
      note.dataset.i18n = `help.${helpKey}`;
      note.textContent = t(`help.${helpKey}`);
    }
    if (code) code.dataset.helpCode = helpKey;
    if (typeof refreshHelpCodes === "function") refreshHelpCodes();
  }
}

document.querySelectorAll('input[name="pocket_kind"]').forEach((r) => {
  r.addEventListener("change", updatePocketFields);
});
updatePocketFields();

btnClearHistory.addEventListener("click", clearHistory);

function showExtractMsg(text, ok) {
  extractMsgEl.textContent = text;
  extractMsgEl.classList.remove("hidden", "ok", "bad");
  extractMsgEl.classList.add(ok ? "ok" : "bad");
}

function renderProfileStatus(st) {
  if (!st) return;
  lastProfileStatus = st;
  dataPathEl.textContent = st.absolute || st.root || "data/profiles/";
  const act = st.active || {};
  if (act.id) {
    const bits = [];
    if (act.trinket_pool) bits.push(t("data.trinketPool"));
    if (act.proc) bits.push(t("data.procTable"));
    dataStatusEl.textContent = t("data.current", {
      id: act.id,
      bits: bits.join(" + ") || t("data.emptyBits"),
    });
  } else if ((st.profiles || []).length === 0) {
    dataStatusEl.textContent = t("data.noProfile");
  } else {
    dataStatusEl.textContent = `${st.profiles.length} profiles`;
  }
}

async function loadProfile() {
  try {
    const res = await fetch("/api/profile");
    const json = await res.json();
    if (json.ok) renderProfileStatus(json);
  } catch {
    dataStatusEl.textContent = t("data.readFail");
  }
}

btnExtract.addEventListener("click", async () => {
  extractMsgEl.classList.add("hidden");
  btnExtract.disabled = true;
  btnExtract.textContent = t("seed.running");
  try {
    const res = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const json = await res.json();
    if (!json.ok) throw new Error(json.error || t("err.fail"));
    const w = (json.warnings || []).join(" ");
    showExtractMsg(
      `${json.profile_dir} trinket=${json.trinket_count}` +
        (json.proc_count ? ` proc=${json.proc_count}` : "") +
        ` ${json.elapsed_sec}s${w ? " " + w : ""}`,
      true
    );
    renderProfileStatus(json.profile_status || json);
  } catch (err) {
    showExtractMsg(err.message || String(err), false);
  } finally {
    btnExtract.disabled = false;
    btnExtract.textContent = t("data.extract");
  }
});

loadProfile();
renderHistoryList();

function heartIcons(count, cls, maxShow = 12) {
  const n = Math.max(0, Math.min(maxShow, Math.round(count)));
  if (n === 0) return `<span class="${cls} empty">·</span>`;
  return `<span class="${cls}">${"♥".repeat(n)}</span>`;
}

function statTone(val) {
  if (!val || val === "±0") return "neutral";
  return val.startsWith("+") ? "up" : val.startsWith("-") ? "down" : "neutral";
}

function render(display) {
  lastDisplay = display;
  const h = display.hearts;
  const statsHtml = (display.stats || [])
    .map(
      (s) => `
      <div class="stat-box">
        <div class="name">${statLabel(s.key)}</div>
        <div class="val ${statTone(s.value)}">${s.value}</div>
      </div>`
    )
    .join("");

  const itemsHtml = (display.items || [])
    .map(
      (it) => `
      <div class="item-box">
        <div class="role">${roleLabel(it.role)}</div>
        <div class="id">${it.id}</div>
      </div>`
    )
    .join("");

  const warns = (display.warnings || []).map((w) => `<p>${w}</p>`).join("");
  const pocket = display.pocket || { trinket_id: "", card_id: "", pill_id: "" };
  const pocketRow = (label, val) =>
    `<div class="pocket-row"><span class="pocket-k">${label}</span><span class="pocket-v">${val ?? ""}</span></div>`;
  const pocketHtml = `
    <div class="pocket-grid">
      ${pocketRow(t("out.trinket"), pocket.trinket_id)}
      ${pocketRow(t("out.card"), pocket.card_id)}
      ${pocketRow(t("out.pill"), pocket.pill_id)}
    </div>`;

  outEl.innerHTML = `
    <div class="run-card">
      <div class="head">${t("out.seed")}</div>
      <div class="body">
        <div class="seed-display">${display.seed}</div>
        ${display.seed_alt ? `<div class="seed-alt">${display.seed_alt}</div>` : ""}
      </div>
    </div>
    <div class="run-card">
      <div class="head">${t("out.hearts")}</div>
      <div class="body hearts-row">
        <div class="heart-group"><div class="label">${t("out.red")}</div><div class="heart-icons">${heartIcons(h.red, "red")}</div></div>
        <div class="heart-group"><div class="label">${t("out.soul")}</div><div class="heart-icons">${heartIcons(h.soul, "soul")}</div></div>
      </div>
    </div>
    <div class="run-card">
      <div class="head">${t("out.stats")}</div>
      <div class="body stats-grid">${statsHtml}</div>
    </div>
    <div class="run-card">
      <div class="head">${t("out.pocket")}</div>
      <div class="body">${pocketHtml}</div>
    </div>
    ${display.has_items ? `<div class="run-card"><div class="head">${t("out.items")}</div><div class="body items-grid">${itemsHtml}</div></div>` : ""}
    ${warns ? `<div class="warn-box">${warns}</div>` : ""}
  `;
  outEl.classList.remove("hidden");
}

function refreshSeedHitLabels() {
  seedListEl.querySelectorAll(".seed-hit .use").forEach((el) => {
    el.textContent = t("history.open");
  });
}

function appendRevLog(line) {
  revLogLines.push(line);
  if (revLogLines.length > 60) revLogLines.shift();
  revLogEl.textContent = revLogLines.join("\n");
  revLogEl.scrollTop = revLogEl.scrollHeight;
}

function resetReverseProgress(clearHits = true) {
  revLogLines.length = 0;
  revLogEl.textContent = "";
  revBarFillEl.style.width = "0%";
  revStatsEl.textContent = "";
  revPhaseEl.textContent = t("rev.ready");
  if (clearHits) {
    seedListEl.innerHTML = "";
    resultsMetaEl.textContent = t("rev.hitsMeta", { n: 0 });
  }
}

function appendSeedHit(seed) {
  const el = document.createElement("div");
  el.className = "seed-hit";
  el.dataset.seed = seed;
  el.innerHTML = `<span class="code">${seed}</span><span class="use">${t("history.open")}</span>`;
  el.addEventListener("click", () => {
    setMode("predict");
    seedEl.value = seed;
    form.requestSubmit();
  });
  seedListEl.appendChild(el);
}

function handleReverseStart(ev) {
  const p = ev.plan || {};
  revPhaseEl.textContent = t("log.mode", { mode: p.mode || "scan", workers: p.workers || 1 });
  appendRevLog(t("log.mode", { mode: p.mode || "scan", workers: p.workers || 1 }));
  if (p.scan_mode === "prefix") {
    appendRevLog(
      t("log.prefixSpan", {
        prefix: p.prefix,
        total: p.prefix_total,
        offset: p.prefix_offset || 0,
      })
    );
  } else {
    appendRevLog(t("log.span", { start: p.start_hex, end: p.end_hex }));
  }
  if (p.filters?.length) appendRevLog(t("log.filters", { v: p.filters.join(", ") }));
  else appendRevLog(t("log.noFilters"));
  (ev.warnings || []).forEach((w) => appendRevLog(`! ${w}`));
}

function handleReverseProgress(ev, hitCount) {
  revPhaseEl.textContent = `${ev.phase} · ${ev.percent}%`;
  revBarFillEl.style.width = `${ev.percent}%`;
  const seedPart = ev.current_seed ? ` ${ev.current_seed}` : "";
  const wPart = ev.workers > 1 ? t("meta.workers", { n: ev.workers }) : "";
  revStatsEl.textContent = t("meta.progress", {
    hex: ev.current_hex,
    seed: seedPart,
    scanned: ev.scanned,
    hits: hitCount,
    rate: ev.rate,
    sec: ev.elapsed_sec,
    workers: wPart,
  });
  resultsMetaEl.textContent = t("meta.hits", { hits: hitCount });
}

async function runReverseStream(body, { fresh = true, round = 1 } = {}) {
  if (fresh) {
    resetReverseProgress(true);
    resetReverseSession();
  } else {
    resetReverseProgress(false);
  }
  reverseWorkspace.classList.remove("hidden");
  reverseAbort = new AbortController();
  body.stream = true;

  const hits = fresh ? [] : [...(reverseSession?.hits || [])];
  let done = null;
  let roundHits = 0;

  const bodyHasPrefix = !!body.seed_prefix;
  appendRevLog(
    fresh
      ? t("log.round1")
      : bodyHasPrefix
        ? t("log.roundPrefix", { n: round, offset: body.prefix_offset || 0 })
        : t("log.roundN", { n: round, start: body.start_u32 })
  );
  showContinueButton(false);

  const res = await fetch("/api/reverse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: reverseAbort.signal,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text.slice(0, 200) || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { value, done: eof } = await reader.read();
    if (eof) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const ev = JSON.parse(line);
      if (ev.type === "start") handleReverseStart(ev);
      else if (ev.type === "progress") handleReverseProgress(ev, hits.length);
      else if (ev.type === "hit") {
        hits.push({ seed: ev.seed, start_seed: ev.start_seed });
        roundHits += 1;
        appendSeedHit(ev.seed);
        appendRevLog(t("log.hit", { n: hits.length, seed: ev.seed }));
        resultsMetaEl.textContent = t("meta.hits", { hits: hits.length });
      } else if (ev.type === "done") done = ev;
      else if (ev.type === "profile") renderProfileStatus(ev.profile);
      else if (ev.type === "error") throw new Error(ev.error || t("err.fail"));
    }
  }

  if (!done) throw new Error(t("err.disconnect"));

  const canContinue = !!done.can_continue;
  const prefixMode = done.scan_mode === "prefix";
  revPhaseEl.textContent = canContinue ? t("rev.roundDone") : t("rev.allDone");
  revBarFillEl.style.width = "100%";
  const totalScanned = (reverseSession?.totalScanned || 0) + done.scanned;
  const nextHint = canContinue
    ? prefixMode
      ? t("meta.nextPrefix", { offset: done.next_prefix_offset })
      : t("meta.next", { hex: done.next_start_hex })
    : "";
  resultsMetaEl.textContent = t("meta.round", {
    hits: hits.length,
    round: done.scanned,
    total: totalScanned,
    next: nextHint,
  });
  const logNext = canContinue
    ? prefixMode
      ? t("log.nextPrefix", { offset: done.next_prefix_offset })
      : t("log.next", { hex: done.next_start_hex })
    : "";
  appendRevLog(
    t("log.roundEnd", {
      n: round,
      scanned: done.scanned,
      hits: roundHits,
      sec: done.elapsed_sec,
      next: logNext,
    })
  );

  if (canContinue) {
    reverseSession = {
      hits,
      totalScanned,
      scanMode: done.scan_mode,
      nextStart: done.next_start_u32,
      nextStartHex: done.next_start_hex,
      nextPrefixOffset: done.next_prefix_offset,
      endU32: done.range_end_u32,
      round,
      baseBody: { ...body },
    };
    if (!prefixMode) setRevStartInput(done.next_start_u32);
    showContinueButton(true);
  } else {
    resetReverseSession();
    saveHistoryEntry({
      mode: "reverse",
      time: new Date().toISOString(),
      criteria: body,
      summary: t("summary.hits", {
        crit: summarizeCriteria(body),
        n: hits.length,
        scanned: totalScanned,
      }),
      matches: hits.slice(0, 20).map((h) => h.seed),
    });
  }

  return done;
}

btnReverseStop.addEventListener("click", () => {
  if (reverseAbort) reverseAbort.abort();
});

function val(id) {
  return document.getElementById(id).value.trim();
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    if (text.trimStart().startsWith("<!DOCTYPE") || text.trimStart().startsWith("<html")) {
      throw new Error(t("err.noApi"));
    }
    throw new Error(text.slice(0, 200) || `HTTP ${res.status}`);
  }
  if (!res.ok && json?.error) {
    const e = new Error(json.error);
    if (json.suggested_seed) e.suggestedSeed = json.suggested_seed;
    throw e;
  }
  return json;
}

function showPredictError(err) {
  const msg = err.message || String(err);
  const sug = err.suggestedSeed;
  errEl.classList.remove("hidden");
  if (sug) {
    errEl.innerHTML = "";
    errEl.append(document.createTextNode(msg + " "));
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "seed-suggest";
    btn.textContent = t("seed.useSuggested", { v: sug });
    btn.addEventListener("click", () => {
      seedEl.value = sug;
      errEl.classList.add("hidden");
      errEl.textContent = "";
      form.requestSubmit();
    });
    errEl.append(btn);
  } else {
    errEl.textContent = msg;
  }
}

function updateReverseScanMode() {
  const prefix = val("rev_prefix");
  const rangeGrid = document.getElementById("revRangeGrid");
  const hasPrefix = !!prefix;
  if (rangeGrid) rangeGrid.classList.toggle("is-disabled", hasPrefix);
  for (const id of ["rev_start", "rev_end"]) {
    const el = document.getElementById(id);
    if (el) el.disabled = hasPrefix;
  }
}

function pickReverseBody() {
  const body = {
    max_results: val("rev_max_results") || "50",
    max_scan: val("rev_max_scan") || "5000000",
    workers: val("rev_workers") || "4",
    ach_159: document.getElementById("rev_ach_159").checked ? "1" : "0",
  };
  const prefix = val("rev_prefix");
  if (prefix) {
    body.seed_prefix = prefix.toUpperCase();
  } else {
    for (const [key, id] of [
      ["start_u32", "rev_start"],
      ["end_u32", "rev_end"],
    ]) {
      const v = val(id);
      if (v) body[key] = v;
    }
  }
  const textFields = [
    ["red", "rev_red"],
    ["soul", "rev_soul"],
    ["damage", "rev_damage"],
    ["speed", "rev_speed"],
    ["tears", "rev_tears"],
    ["range", "rev_range"],
    ["shotSpeed", "rev_shotSpeed"],
    ["luck", "rev_luck"],
    ["passive_id", "rev_passive_id"],
    ["active_id", "rev_active_id"],
  ];
  for (const [key, id] of textFields) {
    const v = val(id);
    if (!v) continue;
    body[key] = v;
  }
  const pk = document.querySelector('input[name="pocket_kind"]:checked')?.value || "";
  if (pk) {
    body.pocket_kind = pk;
    if (pk === "trinket") {
      const tid = val("rev_trinket_id");
      if (tid) body.trinket_id = tid;
    } else if (pk === "card" || pk === "pill") {
      const pid = val("rev_pocket_id");
      if (pid) body.pocket_id = pid;
    }
  }
  return body;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errEl.classList.add("hidden");
  errEl.textContent = "";
  outEl.classList.add("hidden");
  btn.disabled = true;
  btn.textContent = t("seed.running");

  const seed = seedEl.value.trim().toUpperCase();
  const body = {
    seed,
    p3ec: document.getElementById("p3ec").value.trim(),
    ach_159: document.getElementById("ach_159").checked ? "1" : "0",
  };

  try {
    const json = await fetchJson("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!json.ok) throw new Error(json.error || t("err.fail"));
    if (!json.display) throw new Error(t("err.noData"));
    render(json.display);
    if (json.profile) renderProfileStatus(json.profile);
    if (seed) {
      saveHistoryEntry({
        mode: "predict",
        time: new Date().toISOString(),
        seed,
        summary: seed,
      });
    }
  } catch (err) {
    showPredictError(err);
  } finally {
    btn.disabled = false;
    btn.textContent = t("seed.run");
  }
});

reverseForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  errEl.classList.add("hidden");
  outEl.classList.add("hidden");
  btnReverse.disabled = true;
  if (btnReverseContinue) btnReverseContinue.disabled = true;
  btnReverseStop.disabled = false;
  btnReverse.textContent = t("seed.running");

  const body = pickReverseBody();

  try {
    await runReverseStream(body, { fresh: true, round: 1 });
  } catch (err) {
    if (err.name === "AbortError") {
      appendRevLog(t("log.stopped"));
      revPhaseEl.textContent = t("rev.stopped");
    } else {
      errEl.textContent = err.message || String(err);
      errEl.classList.remove("hidden");
    }
  } finally {
    btnReverse.disabled = false;
    if (btnReverseContinue) btnReverseContinue.disabled = false;
    btnReverseStop.disabled = true;
    btnReverse.textContent = t("rev.startScan");
    reverseAbort = null;
  }
});

if (btnReverseContinue) {
  btnReverseContinue.addEventListener("click", async () => {
    if (!reverseSession) return;
    if (reverseSession.scanMode === "prefix") {
      if (reverseSession.nextPrefixOffset == null) return;
    } else if (!reverseSession.nextStartHex) {
      return;
    }
    errEl.classList.add("hidden");
    btnReverse.disabled = true;
    btnReverseContinue.disabled = true;
    btnReverseStop.disabled = false;

    const body = pickReverseBody();
    if (reverseSession.scanMode === "prefix") {
      body.prefix_offset = String(reverseSession.nextPrefixOffset);
    } else {
      body.start_u32 = reverseSession.nextStartHex;
    }
    const round = (reverseSession.round || 1) + 1;

    try {
      await runReverseStream(body, { fresh: false, round });
    } catch (err) {
      if (err.name === "AbortError") {
        appendRevLog(t("log.stopped"));
        revPhaseEl.textContent = t("rev.stopped");
      } else {
        errEl.textContent = err.message || String(err);
        errEl.classList.remove("hidden");
      }
    } finally {
      btnReverse.disabled = false;
      btnReverseContinue.disabled = false;
      btnReverseStop.disabled = true;
      reverseAbort = null;
    }
  });
}

const SEED_ALPHABET = "ABCDEFGHJKLMNPQRSTWXYZ01234V6789";

function formatSeedInput(el) {
  el.addEventListener("input", () => {
    let v = el.value
      .toUpperCase()
      .replace(/\u00a0/g, " ")
      .replace(/I/g, "1")
      .replace(/O/g, "0")
      .replace(/U/g, "V")
      .replace(/5/g, "V");
    v = [...v].filter((c) => c === " " || SEED_ALPHABET.includes(c)).join("");
    if (v.length > 4 && v[4] !== " ") v = v.slice(0, 4) + " " + v.slice(4);
    el.value = v.slice(0, 9);
  });
}
formatSeedInput(seedEl);
const revPrefixEl = document.getElementById("rev_prefix");
formatSeedInput(revPrefixEl);
if (revPrefixEl) {
  revPrefixEl.addEventListener("input", updateReverseScanMode);
  updateReverseScanMode();
}

function onLangChange() {
  if (typeof closeFieldHelp === "function") closeFieldHelp();
  updatePocketFields();
  if (typeof refreshHelpCodes === "function") refreshHelpCodes();
  renderHistoryList();
  if (lastProfileStatus) renderProfileStatus(lastProfileStatus);
  if (lastDisplay && !outEl.classList.contains("hidden")) render(lastDisplay);
  refreshSeedHitLabels();
  if (btn && !btn.disabled) btn.textContent = t("seed.run");
  if (btnReverse && !btnReverse.disabled) btnReverse.textContent = t("rev.startScan");
  if (btnExtract && !btnExtract.disabled) btnExtract.textContent = t("data.extract");
}

const q = new URLSearchParams(location.search);
if (q.get("seed")) {
  seedEl.value = q.get("seed").toUpperCase();
  form.requestSubmit();
}
