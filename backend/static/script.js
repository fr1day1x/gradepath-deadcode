/* -------------------------------------------------------------
   Syllabus What-If — client controller
   Holds the policy in memory, re-renders the editor on changes,
   and debounces /api/calculate calls to re-render results.
   ------------------------------------------------------------- */

const S = {
  policy: null,           // the full policy object
  calcTimer: null,
  lastResult: null,
};

// ---------- DOM helpers --------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const el = (tag, attrs = {}, children = []) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return e;
};
const fmt = (x, digits = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : Number(x).toFixed(digits);

// ---------- Policy helpers -----------------------------------------------
function emptyPolicy() {
  return {
    course_name: "",
    categories: [
      {
        name: "Homework", weight: 50, drop_lowest: 0, drop_min_scores: 0,
        curve_above: null, curve_to: null,
        items: [{ name: "HW 1", score: null, status: "pending" }],
      },
      {
        name: "Final", weight: 50, drop_lowest: 0, drop_min_scores: 0,
        curve_above: null, curve_to: null,
        items: [{ name: "Final Exam", score: null, status: "pending" }],
      },
    ],
    attendance: { weight: 0, drop_fraction: 0.05, marks: [] },
    letter_cutoffs: { A: 90, B: 80, C: 70, D: 60 },
    final_category: "Final",
    final_replaces: "",
  };
}

function attendanceCounts(att) {
  const marks = att?.marks || [];
  return {
    present: marks.filter((m) => m === "present").length,
    late: marks.filter((m) => m === "late").length,
    absent: marks.filter((m) => m === "absent").length,
  };
}
function setAttendanceCounts(att, { present, late, absent }) {
  att.marks = []
    .concat(Array(Math.max(0, present | 0)).fill("present"))
    .concat(Array(Math.max(0, late | 0)).fill("late"))
    .concat(Array(Math.max(0, absent | 0)).fill("absent"));
}

// ---------- Rendering: EDITOR --------------------------------------------
function renderEditor() {
  const p = S.policy;
  $("#course-name").value = p.course_name || "";

  // Categories
  const container = $("#categories");
  container.innerHTML = "";
  const catTpl = $("#t-category");
  p.categories.forEach((cat, ci) => {
    const node = catTpl.content.firstElementChild.cloneNode(true);
    node.dataset.ci = ci;
    node.querySelector(".cat-name").value = cat.name || "";
    node.querySelector(".cat-weight").value = cat.weight ?? "";
    node.querySelector(".cat-drop").value = cat.drop_lowest ?? 0;
    node.querySelector(".cat-dropmin").value = cat.drop_min_scores ?? 0;
    node.querySelector(".cat-curveabove").value = cat.curve_above ?? "";
    node.querySelector(".cat-curveto").value = cat.curve_to ?? "";

    // Items
    const body = node.querySelector(".items-body");
    const itemTpl = $("#t-item");
    cat.items.forEach((item, ii) => {
      const row = itemTpl.content.firstElementChild.cloneNode(true);
      row.dataset.ii = ii;
      row.querySelector(".item-name").value = item.name || "";
      row.querySelector(".item-score").value = item.score ?? "";
      row.querySelector(".item-status").value = item.status || "pending";
      body.appendChild(row);
    });

    container.appendChild(node);
  });

  // Attendance
  const att = p.attendance || (p.attendance = { weight: 0, drop_fraction: 0.05, marks: [] });
  $("#att-weight").value = att.weight ?? 0;
  $("#att-drop").value = att.drop_fraction ?? 0;
  const counts = attendanceCounts(att);
  $("#att-present").value = counts.present;
  $("#att-late").value = counts.late;
  $("#att-absent").value = counts.absent;

  // Cutoffs
  const cutWrap = $("#cutoffs");
  cutWrap.innerHTML = "";
  for (const [letter, val] of Object.entries(p.letter_cutoffs || {})) {
    const row = el("div", { class: "cutoff" }, [
      el("span", { class: "letter" }, letter),
      el("input", {
        type: "number", class: "num", min: "0", max: "100", step: "0.1",
        value: val, "data-letter": letter,
      }),
    ]);
    cutWrap.appendChild(row);
  }

  // Final-rules dropdowns
  const finalSel = $("#final-category");
  const replSel = $("#final-replaces");
  const catNames = p.categories.map((c) => c.name).filter(Boolean);
  finalSel.innerHTML = `<option value="">(none)</option>` +
    catNames.map((n) => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join("");
  replSel.innerHTML = `<option value="">(none)</option>` +
    catNames.map((n) => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join("");
  finalSel.value = p.final_category || "";
  replSel.value = p.final_replaces || "";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------- Rendering: RESULTS --------------------------------------------
function renderResults(r) {
  if (!r) {
    $("#grade-pct").textContent = "—";
    $("#grade-letter").textContent = "—";
    $("#grade-caption").textContent = "Enter a policy to begin";
    $("#whatif-grid").innerHTML = "";
    $("#whatif-sub").textContent = "—";
    $("#best-possible").textContent = "—";
    $("#replacement-note").textContent = "";
    $("#breakdown").innerHTML = "";
    return;
  }

  // Hero
  const cur = r.current || {};
  const grade = cur.grade;
  $("#grade-pct").textContent = grade === null || grade === undefined ? "—" : `${grade.toFixed(1)}%`;
  $("#grade-letter").textContent = cur.letter || "—";

  const totalW = cur.active_weight_total || 0;
  if (grade === null || grade === undefined) {
    $("#grade-caption").textContent = "No scores yet";
  } else {
    const parts = [];
    parts.push(`from ${totalW}% of the grade so far`);
    if (cur.used_replacement) {
      parts.push("final used to replace lowest exam");
    }
    $("#grade-caption").textContent = parts.join(" · ");
  }

  // What-if row
  const wi = r.what_if || { has_final: false, targets: [] };
  const wiGrid = $("#whatif-grid");
  wiGrid.innerHTML = "";
  if (!wi.has_final) {
    $("#whatif-sub").textContent = "No final-exam category set — add one in the editor.";
  } else if (!wi.targets.length) {
    $("#whatif-sub").textContent = "No letter cutoffs defined.";
  } else {
    $("#whatif-sub").textContent = "Score needed on the final to reach each letter";
    for (const t of wi.targets) {
      const cls = ["whatif-cell"];
      let needLabel = "needed on final";
      let needValue;
      if (t.already_locked) {
        cls.push("locked");
        needValue = "✓";
        needLabel = "already locked in";
      } else if (t.not_reachable) {
        cls.push("blocked");
        needValue = "—";
        needLabel = "no longer reachable";
      } else {
        needValue = fmt(t.needed, 1);
      }
      const cell = el("div", { class: cls.join(" ") }, [
        el("div", { class: "wi-letter" }, `${t.letter} · ${t.target}+`),
        el("div", { class: "wi-need" }, String(needValue)),
        el("div", { class: "wi-label" }, needLabel),
      ]);
      // Add replacement-rule aux line when it would help for this letter
      if (!t.already_locked && !t.not_reachable
          && t.needed_without_replacement != null
          && t.needed_with_replacement != null
          && Math.abs(t.needed_without_replacement - t.needed_with_replacement) > 0.5) {
        const better = t.needed_with_replacement < t.needed_without_replacement
          ? `${fmt(t.needed_without_replacement, 1)} without exam replacement`
          : `${fmt(t.needed_with_replacement, 1)} with exam replacement`;
        cell.appendChild(el("div", { class: "wi-aux" }, better));
      }
      wiGrid.appendChild(cell);
    }
  }

  // Best possible + replacement note
  const bp = r.best_possible || {};
  $("#best-possible").textContent =
    bp.grade == null ? "—" : `${bp.grade.toFixed(1)}% · ${bp.letter}${bp.used_replacement ? " (with replacement)" : ""}`;

  const note = [];
  if (cur.replacement_detail) {
    const d = cur.replacement_detail;
    note.push(
      `Final (${fmt(d.with_score, 1)}) replaces lowest ${d.replaced_in} score (${fmt(d.replaced_score, 1)}): ` +
      `${fmt(d.without, 2)}% → ${fmt(d.with, 2)}%`
    );
  }
  $("#replacement-note").textContent = note.join(" ");

  // Breakdown
  const bk = $("#breakdown");
  bk.innerHTML = "";
  for (const [name, c] of Object.entries(r.categories || {})) {
    bk.appendChild(renderRuleRow(name, c, "category"));
  }
  bk.appendChild(renderAttendanceRow(r.attendance));
}

function renderRuleRow(name, c, kind) {
  const weight = c.weight ?? 0;
  const row = el("div", { class: "rule-row" });

  const left = el("div", { class: "rule-cat" }, [
    document.createTextNode(name),
    el("span", { class: "weight-tag" }, `${weight}% weight`),
  ]);

  const body = el("div", { class: "rule-body" });
  if (!c.has_scores) {
    const label = c.pending && c.pending.length
      ? `No scores yet (${c.pending.length} pending). Weight will be renormalized out until a score is entered.`
      : "No scores yet.";
    body.appendChild(el("span", { class: "inactive" }, label));
  } else {
    const pieces = [];
    // Curved
    if (c.curved && c.curved.length) {
      const chunk = el("span", {}, [el("span", { class: "fired" }, "Curved: ")]);
      c.curved.forEach((x, i) => {
        chunk.appendChild(el("span", { class: "pill curve" },
          `${x.name}: ${fmt(x.from, 1)} → ${fmt(x.to, 1)}`));
      });
      pieces.push(chunk);
    }
    // Dropped
    if (c.dropped && c.dropped.length) {
      const chunk = el("span", {}, [el("span", { class: "fired" }, "Dropped: ")]);
      c.dropped.forEach((x) => {
        chunk.appendChild(el("span", { class: "pill drop" },
          `${x.name}: ${fmt(x.score, 1)}`));
      });
      pieces.push(chunk);
    }
    // Included summary
    if (c.included && c.included.length) {
      const scores = c.included.map((x) => fmt(x.score, 0)).join(", ");
      pieces.push(el("span", {}, `Averaged ${c.included.length} item${c.included.length === 1 ? "" : "s"}: ${scores}`));
    }
    if (c.pending && c.pending.length) {
      pieces.push(el("span", { class: "inactive" }, ` · ${c.pending.length} pending`));
    }
    pieces.forEach((p, i) => {
      body.appendChild(p);
      if (i < pieces.length - 1) body.appendChild(document.createTextNode("  "));
    });
  }

  const avgDisplay = c.average == null
    ? el("div", { class: "rule-avg na" }, "—")
    : el("div", { class: "rule-avg" }, `${c.average.toFixed(1)}`);

  row.appendChild(left);
  row.appendChild(body);
  row.appendChild(avgDisplay);
  return row;
}

function renderAttendanceRow(a) {
  const row = el("div", { class: "rule-row" });
  const left = el("div", { class: "rule-cat" }, [
    document.createTextNode("Attendance"),
    el("span", { class: "weight-tag" }, `${a.weight}% weight`),
  ]);
  const body = el("div", { class: "rule-body" });
  if (!a.has_scores) {
    body.appendChild(el("span", { class: "inactive" }, "No marks recorded."));
  } else {
    const parts = [];
    parts.push(document.createTextNode(`${a.total_marks} mark${a.total_marks === 1 ? "" : "s"} recorded`));
    if (a.n_dropped) {
      const chunk = el("span", {}, [
        document.createTextNode(" · "),
        el("span", { class: "fired" }, `Dropped lowest ${a.n_dropped}: `),
      ]);
      a.dropped.forEach((d) => {
        chunk.appendChild(el("span", { class: "pill drop" },
          `#${d.index + 1} ${d.status}`));
      });
      parts.push(chunk);
    }
    parts.push(document.createTextNode(` · averaged ${a.included_count}`));
    parts.forEach((p) => body.appendChild(p));

    // Absence warning
    const absents = a.dropped.filter((d) => d.status === "absent").length;
    const absentCapacity = a.n_dropped;
    if (absentCapacity > 0 && absents >= absentCapacity) {
      const warn = el("div", {}, [
        el("span", { class: "fired" }, "Heads up: "),
        document.createTextNode("you have used your dropped-attendance buffer. The next absence will count."),
      ]);
      body.appendChild(el("br"));
      body.appendChild(warn);
    }
  }
  const avg = a.average == null
    ? el("div", { class: "rule-avg na" }, "—")
    : el("div", { class: "rule-avg" }, `${a.average.toFixed(1)}`);
  row.appendChild(left);
  row.appendChild(body);
  row.appendChild(avg);
  return row;
}

// ---------- Event wiring --------------------------------------------------
function bindEvents() {
  $("#course-name").addEventListener("input", (e) => {
    S.policy.course_name = e.target.value;
    scheduleCalc();
  });

  $("#add-category").addEventListener("click", () => {
    S.policy.categories.push({
      name: "New Category", weight: 0, drop_lowest: 0, drop_min_scores: 0,
      curve_above: null, curve_to: null,
      items: [{ name: "Item 1", score: null, status: "pending" }],
    });
    renderEditor();
    scheduleCalc();
  });

  $("#load-sample").addEventListener("click", async () => {
    const r = await fetch("/api/sample");
    S.policy = await r.json();
    renderEditor();
    runCalc(0);
  });

  $("#save-policy").addEventListener("click", async () => {
    const name = prompt("Save as:", S.policy.course_name || "my-course");
    if (!name) return;
    const r = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, policy: S.policy }),
    });
    if (r.ok) {
      await refreshSavedList();
      flash(`Saved as "${name}"`);
    } else {
      const data = await r.json().catch(() => ({}));
      flash(`Save failed: ${data.error || r.status}`, true);
    }
  });

  $("#load-policy").addEventListener("change", async (e) => {
    const name = e.target.value;
    if (!name) return;
    const r = await fetch(`/api/saved/${encodeURIComponent(name)}`);
    if (r.ok) {
      S.policy = await r.json();
      renderEditor();
      runCalc(0);
    }
    e.target.value = "";
  });

  // Delegated editor events
  $("#categories").addEventListener("input", onEditorInput);
  $("#categories").addEventListener("change", onEditorInput);
  $("#categories").addEventListener("click", onEditorClick);

  // Attendance
  for (const id of ["#att-weight", "#att-drop", "#att-present", "#att-late", "#att-absent"]) {
    $(id).addEventListener("input", () => {
      const att = S.policy.attendance;
      att.weight = parseFloat($("#att-weight").value) || 0;
      att.drop_fraction = parseFloat($("#att-drop").value) || 0;
      setAttendanceCounts(att, {
        present: parseInt($("#att-present").value, 10) || 0,
        late: parseInt($("#att-late").value, 10) || 0,
        absent: parseInt($("#att-absent").value, 10) || 0,
      });
      scheduleCalc();
    });
  }

  // Cutoffs
  $("#cutoffs").addEventListener("input", (e) => {
    const letter = e.target.getAttribute("data-letter");
    if (!letter) return;
    const v = parseFloat(e.target.value);
    if (!Number.isNaN(v)) S.policy.letter_cutoffs[letter] = v;
    scheduleCalc();
  });

  $("#final-category").addEventListener("change", (e) => {
    S.policy.final_category = e.target.value;
    scheduleCalc();
  });
  $("#final-replaces").addEventListener("change", (e) => {
    S.policy.final_replaces = e.target.value;
    scheduleCalc();
  });
}

function onEditorInput(e) {
  const t = e.target;
  const catNode = t.closest(".category");
  if (!catNode) return;
  const ci = +catNode.dataset.ci;
  const cat = S.policy.categories[ci];

  if (t.classList.contains("cat-name")) {
    const old = cat.name;
    cat.name = t.value;
    if (S.policy.final_category === old) S.policy.final_category = cat.name;
    if (S.policy.final_replaces === old) S.policy.final_replaces = cat.name;
    // Need to refresh dropdowns
    const finalSel = $("#final-category");
    const replSel = $("#final-replaces");
    const names = S.policy.categories.map((c) => c.name).filter(Boolean);
    const build = (sel, val) => {
      sel.innerHTML = `<option value="">(none)</option>` +
        names.map((n) => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join("");
      sel.value = val || "";
    };
    build(finalSel, S.policy.final_category);
    build(replSel, S.policy.final_replaces);
  } else if (t.classList.contains("cat-weight")) cat.weight = parseFloat(t.value) || 0;
  else if (t.classList.contains("cat-drop")) cat.drop_lowest = parseInt(t.value, 10) || 0;
  else if (t.classList.contains("cat-dropmin")) cat.drop_min_scores = parseInt(t.value, 10) || 0;
  else if (t.classList.contains("cat-curveabove")) cat.curve_above = t.value === "" ? null : parseFloat(t.value);
  else if (t.classList.contains("cat-curveto")) cat.curve_to = t.value === "" ? null : parseFloat(t.value);
  else {
    const row = t.closest(".item");
    if (!row) return;
    const ii = +row.dataset.ii;
    const item = cat.items[ii];
    if (t.classList.contains("item-name")) item.name = t.value;
    else if (t.classList.contains("item-score")) {
      item.score = t.value === "" ? null : parseFloat(t.value);
      if (item.score !== null && item.status === "pending") {
        item.status = "scored";
        row.querySelector(".item-status").value = "scored";
      }
    } else if (t.classList.contains("item-status")) item.status = t.value;
  }
  scheduleCalc();
}

function onEditorClick(e) {
  const t = e.target;
  const catNode = t.closest(".category");
  if (!catNode) return;
  const ci = +catNode.dataset.ci;
  const cat = S.policy.categories[ci];

  if (t.classList.contains("cat-remove")) {
    S.policy.categories.splice(ci, 1);
    renderEditor();
    scheduleCalc();
  } else if (t.classList.contains("add-item")) {
    cat.items.push({ name: `Item ${cat.items.length + 1}`, score: null, status: "pending" });
    renderEditor();
    scheduleCalc();
  } else if (t.classList.contains("item-remove")) {
    const row = t.closest(".item");
    const ii = +row.dataset.ii;
    cat.items.splice(ii, 1);
    renderEditor();
    scheduleCalc();
  }
}

// ---------- Calc orchestration -------------------------------------------
function scheduleCalc() {
  clearTimeout(S.calcTimer);
  S.calcTimer = setTimeout(() => runCalc(0), 150);
}

async function runCalc() {
  try {
    const r = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy: S.policy }),
    });
    const data = await r.json();
    if (!r.ok) {
      renderResults(null);
      flash(data.error || "Could not calculate", true);
      return;
    }
    S.lastResult = data;
    renderResults(data);
  } catch (e) {
    flash("Could not reach the server", true);
  }
}

// ---------- Saved list ---------------------------------------------------
async function refreshSavedList() {
  const r = await fetch("/api/saved");
  const data = await r.json();
  const sel = $("#load-policy");
  sel.innerHTML = `<option value="">Open saved…</option>` +
    data.saved.map((n) => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join("");
}

// ---------- Flash messages -----------------------------------------------
let flashTimer = null;
function flash(msg, isError = false) {
  let r = $(".error-ribbon");
  if (!r) {
    r = document.createElement("div");
    r.className = "error-ribbon";
    document.body.appendChild(r);
  }
  r.textContent = msg;
  r.style.background = isError ? "#FFF3F0" : "#EEF4EA";
  r.style.color = isError ? "#7E2B22" : "#184D34";
  r.style.borderColor = isError ? "#D8B2AC" : "#B9D3B5";
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => r.remove(), 2500);
}

// ---------- Boot ---------------------------------------------------------
async function boot() {
  // Load sample on first visit so judges see numbers immediately
  try {
    const r = await fetch("/api/sample");
    S.policy = await r.json();
  } catch {
    S.policy = emptyPolicy();
  }
  renderEditor();
  bindEvents();
  refreshSavedList();
  runCalc(0);
}

boot();
