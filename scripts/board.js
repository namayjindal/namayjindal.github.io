/* namay.xyz — assembles the printed layers into an interactive softboard.
   manifest.json is written by riso/generate.py: id, position, size, blend, hover.
   The left column is live HTML text, so the baked "type" layers are skipped here. */

const RISO = "/assets/riso";
const SKIP = new Set(["type", "type-accent", "logo", "_tooth"]);

const $ = (s) => document.querySelector(s);

async function main() {
  const [manifest, content] = await Promise.all([
    fetch(`${RISO}/manifest.json`).then((r) => r.json()),
    fetch(`${RISO}/content.json`).then((r) => r.json()),
  ]);

  fillColumn(content);
  const notes = buildStage(manifest, content);
  wirePanel(content, notes);
  fitStage(manifest);
  requestAnimationFrame(() => fitStage(manifest));   // re-measure once fonts settle
  addEventListener("resize", () => fitStage(manifest));
}

/* ---------------------------------------------------------------- left column */
function fillColumn(c) {
  $(".wordmark").textContent = c.name;
  $(".tagline").textContent = c.tagline;
  $(".blurb").textContent = c.blurb;
  $(".hint").textContent = c.hint;

  $(".jump").innerHTML = "";
  for (const n of c.notes) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = n.heading;
    b.dataset.open = n.id;
    $(".jump").append(b);
  }
  $(".contacts").innerHTML = c.contacts
    .map((x) => `<li><a href="${x.url}"${x.url.startsWith("http") ? ' target="_blank" rel="noopener"' : ""}>${x.label}</a></li>`)
    .join("");
}

/* ---------------------------------------------------------------- board */
function buildStage(m, content) {
  const stage = $("#stage");
  const ext = m.ext || "png";
  const headings = Object.fromEntries(content.notes.map((n) => [n.id, n.heading]));
  const notes = {};

  // The generated canvas includes the left type column, which the site renders as
  // live HTML. Crop the stage to what we actually paint so nothing scales dead space.
  const drawn = m.elements.filter((e) => !SKIP.has(e.id));
  const box = {
    x: Math.min(...drawn.map((e) => e.x)), y: Math.min(...drawn.map((e) => e.y)),
    r: Math.max(...drawn.map((e) => e.x + e.w)), b: Math.max(...drawn.map((e) => e.y + e.h)),
  };
  m.box = [box.r - box.x, box.b - box.y];
  stage.style.setProperty("--stage-w", m.box[0]);
  stage.style.setProperty("--stage-h", m.box[1]);

  for (const el of m.elements) {
    if (SKIP.has(el.id)) continue;

    const img = new Image();
    img.src = `${RISO}/${el.id}.${ext}`;
    img.alt = "";
    img.decoding = "async";
    img.width = el.w;
    img.height = el.h;
    Object.assign(img.style, { left: `${el.x - box.x}px`, top: `${el.y - box.y}px`, width: `${el.w}px`, height: `${el.h}px` });
    if (el.blend === "multiply") img.classList.add("multiply");
    if (el.id.endsWith("-shadow")) img.classList.add("shadow");

    if (el.hover) {
      // a hoverable note is a real button so it is keyboard and screen-reader reachable
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "note";
      btn.dataset.open = el.hover;
      btn.setAttribute("aria-label", `open ${headings[el.hover] || el.hover}`);
      Object.assign(btn.style, { left: `${el.x - box.x}px`, top: `${el.y - box.y}px`, width: `${el.w}px`, height: `${el.h}px` });
      img.style.left = img.style.top = "0";
      btn.append(img);
      stage.append(btn);
      notes[el.hover] = btn;
    } else {
      stage.append(img);
    }
  }

  // the shadow sits below its note in paint order, so link them by hand
  for (const [id, btn] of Object.entries(notes)) {
    const sh = stage.querySelector(`img[src$="${id}-shadow.${ext}"]`);
    if (!sh) continue;
    const on = () => sh.classList.add("lift");
    const off = () => sh.classList.remove("lift");
    btn.addEventListener("mouseenter", on);
    btn.addEventListener("mouseleave", off);
    btn.addEventListener("focus", on);
    btn.addEventListener("blur", off);
  }
  return notes;
}

/* keep the 1800x1150 print at its own scale, fitted to whatever space it gets */
function fitStage(m) {
  const wrap = $(".board-wrap");
  const fit = $(".stage-fit");
  const [w, h] = m.box || m.canvas;
  // collapse the sizer first, otherwise we measure last frame's board, not free space
  fit.style.width = fit.style.height = "0px";
  const pagePad = parseFloat(getComputedStyle($(".page")).paddingTop) || 24;
  const stacked = matchMedia("(max-width: 900px)").matches;
  const availH = innerHeight - pagePad * 2;
  const byW = (wrap.clientWidth - 4) / w;
  const s = Math.max(0.1, stacked ? byW : Math.min(byW, availH / h, 1.25));
  $("#stage").style.setProperty("--scale", s);
  // the stage keeps its full 1:1 layout size, so the wrapper carries the scaled box
  fit.style.width = `${w * s}px`;
  fit.style.height = `${h * s}px`;
}

/* ---------------------------------------------------------------- panel */
function wirePanel(content, notes) {
  const panel = $("#panel");
  const heading = $("#panel-heading");
  const body = $("#panel-body");
  const byId = Object.fromEntries(content.notes.map((n) => [n.id, n]));
  let lastFocus = null;

  function open(id) {
    const n = byId[id];
    if (!n) return;
    heading.textContent = n.heading;
    body.innerHTML = n.body.map((p) => `<p>${p}</p>`).join("");
    lastFocus = document.activeElement;
    panel.hidden = false;
    $("#panel-close").focus();
    history.replaceState(null, "", `#${id}`);
  }

  function close() {
    panel.hidden = true;
    history.replaceState(null, "", location.pathname);
    if (lastFocus) lastFocus.focus();
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-open]");
    if (t) return open(t.dataset.open);
    if (e.target === panel) close();
  });
  $("#panel-close").addEventListener("click", close);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) close();
  });

  const hash = location.hash.slice(1);
  if (hash && byId[hash]) open(hash);
  void notes;
}

main().catch((err) => {
  console.error("[board] failed to build:", err);
  document.body.classList.add("board-error");
});
